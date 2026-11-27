from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from passes.models import PassApplication
from verification.models import EMISStudent


class SchoolAdminDuplicateStudentIdTests(TestCase):
	def test_school_apply_handles_duplicate_student_ids_gracefully(self):
		self.user = get_user_model().objects.create_user(
			username="vijayawadagovernme_demo",
			password="Demo@d0776dce89",
		)
		self.client.force_login(self.user)
		session = self.client.session
		session["admin_type"] = "school"
		session["admin_username"] = "vijayawadagovernme_demo"
		session.save()

		EMISStudent.objects.create(
			student_id="EMIS-AND-001",
			student_name="Meena Patel",
			school_name="Vijayawada Government Higher Secondary School",
			class_name="10-A",
			academic_year="2025-2026",
			state="Andhra Pradesh",
		)
		EMISStudent.objects.create(
			student_id="EMIS-AND-001",
			student_name="Arun Patel",
			school_name="Vijayawada Government Higher Secondary School",
			class_name="10-A",
			academic_year="2025-2026",
			state="Andhra Pradesh",
		)

		response = self.client.post(
			reverse("school_apply"),
			data={"student_id": "EMIS-AND-001"},
			follow=True,
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Student record verified")


class TransportCollegePortalRedirectTests(TestCase):
	def setUp(self):
		self.user = get_user_model().objects.create_user(
			username="adminuser",
			password="testpass123",
			is_staff=True,
		)

	def test_transport_send_college_redirects_to_college_portal(self):
		application = PassApplication.objects.create(
			application_number="COL-REDIRECT-1",
			pass_type="COLLEGE",
			status="TRANSPORT_VERIFICATION",
			full_name="Test Student",
		)

		self.client.force_login(self.user)
		response = self.client.post(
			reverse("transport_send_college", args=[application.id]),
			data={"remarks": "Sent to college review"},
			follow=False,
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(
			response.url,
			reverse("transport_college_portal"),
		)

	def test_transport_allow_payment_redirects_to_college_portal(self):
		application = PassApplication.objects.create(
			application_number="COL-REDIRECT-2",
			pass_type="COLLEGE",
			status="COLLEGE_APPROVED",
			full_name="Approved Student",
		)

		self.client.force_login(self.user)
		response = self.client.post(
			reverse("transport_allow_payment", args=[application.id]),
			data={"remarks": "Payment approved"},
			follow=False,
		)

		self.assertEqual(response.status_code, 302)
		self.assertEqual(
			response.url,
			reverse("transport_college_portal"),
		)

	def test_transport_dashboard_contains_live_overview_metrics(self):
		self.client.force_login(self.user)
		response = self.client.get(reverse("transport_admin"))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, "Total applications")
		self.assertContains(response, "E-passes generated")
		self.assertContains(response, "School Students")
