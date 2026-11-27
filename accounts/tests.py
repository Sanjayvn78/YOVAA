from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from passes.models import EPass, PassApplication
from verification.models import GovernmentTransportStaff

from .models import UserProfile

class GeneralAccountFlowTests(TestCase):
	def test_general_register_creates_account_and_logs_in(self):
		response = self.client.post(
			reverse("general_register"),
			{
				"name": "General User",
				"phone_number": "9876543210",
				"password": "StrongPass123!",
				"confirm_password": "StrongPass123!",
			},
		)

		self.assertRedirects(response, reverse("general_dashboard"))
		self.assertTrue(
			UserProfile.objects.filter(
				phone_number="9876543210",
				user_type="GENERAL",
			).exists()
		)

	def test_general_login_redirects_to_dashboard(self):
		self.client.post(
			reverse("general_register"),
			{
				"name": "General User",
				"phone_number": "9876543211",
				"password": "StrongPass123!",
				"confirm_password": "StrongPass123!",
			},
		)
		self.client.get(reverse("account_logout"))

		response = self.client.post(
			reverse("general_login"),
			{
				"identifier": "9876543211",
				"password": "StrongPass123!",
			},
		)

		self.assertRedirects(response, reverse("general_dashboard"))


class SpecialStaffLoginTests(TestCase):
	def setUp(self):
		self.staff = GovernmentTransportStaff.objects.create(
			staff_number="PERM-1001",
			name="Permanent Staff",
			department="Operations",
			designation="Inspector",
			workplace="Central Depot",
			employment_status="PERMANENT",
			is_eligible=True,
			is_active=True,
		)

	def test_staff_id_login_opens_generate_pass_dashboard(self):
		response = self.client.post(
			reverse("special_login"),
			{"identifier": self.staff.staff_number},
		)

		self.assertRedirects(response, reverse("special_dashboard"))
		dashboard = self.client.get(reverse("special_dashboard"))
		self.assertContains(dashboard, "Generate Pass")
		self.assertNotContains(dashboard, "Renewal")

		documents_response = self.client.get(reverse("special_generate_pass"))
		self.assertEqual(documents_response.status_code, 200)
		self.assertContains(documents_response, "Staff ID Card")
		self.assertContains(documents_response, "Address Proof")
		self.assertFalse(PassApplication.objects.filter(staff_number=self.staff.staff_number).exists())

		pass_response = self.client.post(
			reverse("special_generate_pass"),
			{
				"applicant_photo": SimpleUploadedFile(
					"staff-photo.png", b"photo", content_type="image/png"
				),
				"address_proof_document": SimpleUploadedFile(
					"address-proof.pdf", b"address", content_type="application/pdf"
				),
				"signature_document": SimpleUploadedFile(
					"signature.pdf", b"signature", content_type="application/pdf"
				),
				"staff_id_card_document": SimpleUploadedFile(
					"staff-card.pdf", b"staff-card", content_type="application/pdf"
				),
			},
		)

		self.assertEqual(pass_response.status_code, 200)
		application = PassApplication.objects.get(
			pass_type="SPECIAL",
			staff_number=self.staff.staff_number,
		)
		self.assertEqual(application.status, "APPROVED")
		self.assertTrue(EPass.objects.filter(application=application).exists())
		self.assertContains(pass_response, self.staff.name)
		self.assertTrue(application.applicant_photo)
		self.assertTrue(application.address_proof_document)
		self.assertTrue(application.signature_document)
		self.assertTrue(application.staff_id_card_document)

	def test_non_permanent_staff_cannot_login(self):
		self.staff.employment_status = "CONTRACT"
		self.staff.save(update_fields=["employment_status"])

		response = self.client.post(
			reverse("special_login"),
			{"identifier": self.staff.staff_number},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Only active permanent staff")
		self.assertNotIn("special_staff_id", self.client.session)

	def test_special_registration_redirects_to_login(self):
		response = self.client.get(reverse("special_register"))

		self.assertRedirects(response, reverse("special_login"))
