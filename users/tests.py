from datetime import timedelta

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from django.contrib.auth import get_user_model
from passes.models import EPass, PassApplication
from payments.models import Payment
from users.views import calculate_pass_fee
from verification.management.commands.import_demo_data import parse_umis
from verification.models import GovernmentTransportStaff, UMISStudent


class CalculatePassFeeTests(SimpleTestCase):
    def test_general_new_fee_is_application_and_registration_fee(self):
        self.assertEqual(
            calculate_pass_fee(
                "Singanallur to Gandhipuram",
                "Singanallur Bus Terminus",
                "Gandhipuram Town Bus Stand",
                pass_type="GENERAL",
            ),
            1100.00,
        )

    def test_renewal_flag_is_ignored_and_application_is_treated_as_new(self):
        self.assertEqual(
            calculate_pass_fee(
                "Singanallur to Gandhipuram",
                "Singanallur Bus Terminus",
                "Gandhipuram Town Bus Stand",
                pass_type="GENERAL",
                application_type="RENEWAL",
            ),
            1100.00,
        )
        self.assertEqual(
            calculate_pass_fee(
                "Singanallur to Gandhipuram",
                "Singanallur Bus Terminus",
                "Gandhipuram Town Bus Stand",
                pass_type="DISABLED",
                application_type="RENEWAL",
            ),
            550.00,
        )

    def test_base_fee_increases_by_30_per_stop(self):
        self.assertEqual(
            calculate_pass_fee(
                "Singanallur to Gandhipuram",
                "Singanallur Bus Terminus",
                "ESI Hospital",
            ),
            230.00,
        )
        self.assertEqual(
            calculate_pass_fee(
                "Singanallur to Gandhipuram",
                "Singanallur Bus Terminus",
                "Gandhipuram Town Bus Stand",
            ),
            200.00 + (30 * 6),
        )
        self.assertEqual(
            calculate_pass_fee(
                "Singanallur to Gandhipuram",
                "Gandhipuram Town Bus Stand",
                "Singanallur Bus Terminus",
            ),
            200.00 + (30 * 6),
        )


class DemoDataImportParserTests(SimpleTestCase):
    def test_parse_umis_accepts_years_and_four_digit_reference_ids(self):
        row = [
            "UMIS-1234",
            "REG-1234",
            "Student Name",
            "Computer Science",
            "Coimbatore Institute of Technology",
            "2024-2025",
            "2",
        ]

        students = parse_umis([row], "Tamil Nadu")

        self.assertEqual(len(students), 1)
        self.assertEqual(students[0].registration_number, "REG-1234")
        self.assertEqual(students[0].college_name, "Coimbatore Institute of Technology")
        self.assertEqual(students[0].academic_year, "2024-2025")
        self.assertEqual(students[0].year, "2")


class CollegePassDuplicateUmisTests(TestCase):
    def test_college_apply_verifies_student_before_form(self):
        user = get_user_model().objects.create_user(
            username="college-verify-user",
            password="pass123",
        )
        student = UMISStudent.objects.create(
            umis_number="UMIS-5001",
            registration_number="REG-5001",
            name="Verified Student",
            college_name="Coimbatore Institute of Technology",
            department="Computer Science",
            course="B.E.",
            year="2",
            academic_year="2024 - 2025",
            state="Tamil Nadu",
            is_active=True,
        )

        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("college_apply"),
            {"registration_number": student.registration_number},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "UMIS Verification Successful")
        self.assertContains(response, student.name)

    def test_college_apply_blocks_duplicate_active_student(self):
        user = get_user_model().objects.create_user(
            username="college-duplicate-user",
            password="pass123",
        )
        student = UMISStudent.objects.create(
            umis_number="UMIS-9001",
            registration_number="REG-9001",
            name="Duplicate Student",
            college_name="Coimbatore Institute of Technology",
            department="Computer Science",
            course="B.E.",
            year="2",
            academic_year="2024 - 2025",
            state="Tamil Nadu",
            is_active=True,
        )
        PassApplication.objects.create(
            application_number="COL-DUP-1",
            applicant=user,
            pass_type="COLLEGE",
            status="PAYMENT_COMPLETED",
            full_name=student.name,
            registration_number=student.registration_number,
            college_name=student.college_name,
            department=student.department,
        )

        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("college_apply"),
            {"registration_number": student.registration_number},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already has a college pass active")

    def test_college_details_creates_payment_pending_application(self):
        user = get_user_model().objects.create_user(
            username="college-app-user",
            password="pass123",
        )
        student = UMISStudent.objects.create(
            umis_number="UMIS-6001",
            registration_number="REG-6001",
            name="Final Student",
            college_name="Coimbatore Institute of Technology",
            department="Computer Science",
            course="B.E.",
            year="1",
            academic_year="2024 - 2025",
            state="Tamil Nadu",
            is_active=True,
        )
        photo = SimpleUploadedFile("student-photo.png", b"fake-photo", content_type="image/png")
        aadhaar = SimpleUploadedFile("aadhaar.pdf", b"fake-pdf", content_type="application/pdf")
        signature = SimpleUploadedFile("signature.pdf", b"fake-pdf", content_type="application/pdf")

        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("college_details"),
            {
                "student_id": student.id,
                "state": "Tamil Nadu",
                "district": "Coimbatore",
                "route": "Singanallur to Gandhipuram",
                "start_point": "Singanallur Bus Terminus",
                "destination_point": "Gandhipuram Town Bus Stand",
                "applicant_photo": photo,
                "aadhaar_document": aadhaar,
                "signature_document": signature,
            },
        )

        application = PassApplication.objects.filter(pass_type="COLLEGE", applicant=user).latest("created_at")
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("payment", args=[application.id]))
        self.assertEqual(application.status, "PAYMENT_PENDING")
        self.assertEqual(application.registration_number, student.registration_number)
        self.assertEqual(application.college_name, student.college_name)


class EPassStudentPhotoTests(TestCase):
    def test_epass_page_displays_student_photo_and_qr(self):
        user = get_user_model().objects.create_user(
            username="studentphoto",
            password="pass123",
        )
        photo = SimpleUploadedFile(
            "student-photo.png",
            b"fake-image-data",
            content_type="image/png",
        )
        application = PassApplication.objects.create(
            application_number="E-PASS-PHOTO-1",
            applicant=user,
            pass_type="COLLEGE",
            status="PAYMENT_COMPLETED",
            full_name="Test Student",
            route="Singanallur to Gandhipuram",
            start_point="Singanallur Bus Terminus",
            destination_point="Gandhipuram Town Bus Stand",
            applicant_photo=photo,
        )
        pass_obj = EPass.objects.create(
            application=application,
            pass_number="YOVAA-EPASS-001",
            expiry_date="2026-09-10",
            valid_from="2026-09-10",
            valid_until="2026-10-10",
            qr_data="YOVAA-EPASS-001",
        )
        pass_obj.qr_code.save(
            "qr-code.png",
            ContentFile(b"fake-qr-data"),
            save=True,
        )

        client = Client()
        client.force_login(user)
        response = client.get(reverse("epass", args=[application.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, application.applicant_photo.name)
        self.assertContains(response, pass_obj.qr_code.name)


class EPassAccessTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(
            username="epass-owner",
            password="pass123",
        )
        self.other_user = get_user_model().objects.create_user(
            username="epass-other",
            password="pass123",
        )
        application = PassApplication.objects.create(
            application_number="E-PASS-ACCESS-1",
            applicant=self.owner,
            pass_type="GENERAL",
            status="PAYMENT_COMPLETED",
            full_name="Pass Owner",
        )
        self.pass_obj = EPass.objects.create(
            application=application,
            pass_number="YOVAA-ACCESS-001",
            expiry_date="2026-09-10",
        )

    def test_e_pass_requires_the_application_owner(self):
        client = Client()
        self.assertEqual(
            client.get(reverse("e_pass", args=[self.pass_obj.id])).status_code,
            302,
        )
        client.force_login(self.other_user)
        self.assertEqual(
            client.get(reverse("e_pass", args=[self.pass_obj.id])).status_code,
            404,
        )
        client.force_login(self.owner)
        self.assertEqual(
            client.get(reverse("e_pass", args=[self.pass_obj.id])).status_code,
            200,
        )

    def test_epass_download_returns_pdf_file(self):
        client = Client()
        client.force_login(self.owner)

        response = client.get(
            reverse("epass_download", args=[self.pass_obj.application.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))

    def test_epass_html_download_returns_html_file(self):
        client = Client()
        client.force_login(self.owner)

        response = client.get(
            reverse("epass_html_download", args=[self.pass_obj.application.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/html; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        self.assertIn("YOVAA", response.content.decode("utf-8"))
        self.assertIn("data:image", response.content.decode("utf-8"))
        self.assertIn("Pass Issued On", response.content.decode("utf-8"))

    def test_epass_html_download_allows_approved_staff_pass_without_applicant(self):
        staff_user = get_user_model().objects.create_user(
            username="staff-epass-user",
            password="pass123",
            is_staff=True,
        )
        application = PassApplication.objects.create(
            application_number="SPECIAL-APPROVED-1",
            applicant=None,
            pass_type="SPECIAL",
            status="APPROVED",
            full_name="Approved Staff",
        )
        EPass.objects.create(
            application=application,
            pass_number="YOVAA-APPROVED-001",
            expiry_date="2026-09-10",
            qr_data="YOVAA-APPROVED-001",
        )

        client = Client()
        client.force_login(staff_user)

        response = client.get(
            reverse("epass_html_download", args=[application.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("YOVAA", response.content.decode("utf-8"))


class SchoolEPassFlowTests(TestCase):
    def setUp(self):
        self.application = PassApplication.objects.create(
            application_number="SCHOOL-EPASS-1",
            pass_type="SCHOOL",
            status="PAYMENT_PENDING",
            full_name="School Student",
            route="Singanallur to Gandhipuram",
            start_point="Singanallur Bus Terminus",
            destination_point="Gandhipuram Town Bus Stand",
        )
        Payment.objects.create(
            application=self.application,
            amount=30,
            status="PENDING",
        )

    def test_school_payment_verification_works_without_login(self):
        client = Client()
        session = client.session
        session["school_payment_application_id"] = self.application.id
        session.save()

        response = client.get(
            reverse("payment_verify", args=[self.application.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Payment submitted")

    def test_school_student_can_open_generated_epass(self):
        self.application.status = "PAYMENT_COMPLETED"
        self.application.save(update_fields=["status"])
        pass_obj = EPass.objects.create(
            application=self.application,
            pass_number="YOVAA-SCHOOL-001",
            expiry_date="2027-09-14",
        )
        Payment.objects.filter(application=self.application).update(status="SUCCESS")
        client = Client()
        session = client.session
        session["school_payment_application_id"] = self.application.id
        session.save()

        response = client.get(
            reverse("payment_success", args=[self.application.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("e_pass", args=[pass_obj.id]))

    def test_school_student_can_access_epass_via_session_when_application_has_no_owner(self):
        self.application.applicant = None
        self.application.status = "PAYMENT_COMPLETED"
        self.application.save(update_fields=["applicant", "status"])
        pass_obj = EPass.objects.create(
            application=self.application,
            pass_number="YOVAA-SCHOOL-002",
            expiry_date="2027-09-14",
        )
        Payment.objects.filter(application=self.application).update(status="SUCCESS")

        client = Client()
        client.force_login(
            get_user_model().objects.create_user(
                username="school-session-user",
                password="pass123",
            )
        )
        session = client.session
        session["school_payment_application_id"] = self.application.id
        session.save()

        response = client.get(reverse("e_pass", args=[pass_obj.id]))

        self.assertEqual(response.status_code, 200)


class GeneralPassAccessTests(TestCase):
    def test_legacy_general_pass_redirects_to_general_login(self):
        response = self.client.get(reverse("general_pass_legacy"))

        self.assertRedirects(
            response,
            "/accounts/login/general/?next=/users/general-pass/",
        )


class SpecialPassRegistrationTests(TestCase):
    def setUp(self):
        self.staff = GovernmentTransportStaff.objects.create(
            staff_number="IPO-1001",
            name="Special Staff",
            department="Operations",
            designation="Inspector",
            workplace="Central Depot",
            employment_status="ACTIVE",
            is_eligible=True,
            is_active=True,
        )

    def test_legacy_special_application_route_redirects_to_login(self):
        response = self.client.get(
            reverse("special_apply"),
        )

        self.assertRedirects(response, "/accounts/special/login/")
