from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class PassApplication(models.Model):

	PASS_TYPE_CHOICES = [
		("COLLEGE", "College Bus Pass"),
		("DISABLED", "Disabled Person Pass"),
		("GENERAL", "General Pass"),
		("SPECIAL", "Special Pass"),
		("SCHOOL", "School Pass"),
	]

	STATUS_CHOICES = [
		("DRAFT", "Draft"),
		("SUBMITTED", "Submitted"),
		("VERIFICATION", "Verification"),
		("COLLEGE_VERIFICATION", "College Verification"),
		("SCHOOL_VERIFICATION", "School Verification"),
		("DISABLED_VERIFICATION", "Disabled Verification"),
		("GENERAL_VERIFICATION", "General Verification"),
		("SPECIAL_VERIFICATION", "Special Verification"),
		("TRANSPORT_VERIFICATION", "Transport Verification"),
		("PAYMENT_PENDING", "Payment Pending"),
		("PAYMENT_COMPLETED", "Payment Completed"),
		("COLLEGE_APPROVED", "College Approved"),
		("COLLEGE_REJECTED", "College Rejected"),
		("SCHOOL_APPROVED", "School Approved"),
		("SCHOOL_REJECTED", "School Rejected"),
		("APPROVED", "Approved"),
		("REJECTED", "Rejected"),
	]

	APPLICATION_TYPE_CHOICES = [
		("NEW", "New Application"),
		("RENEWAL", "Renewal"),
	]

	application_number = models.CharField(
		max_length=30,
		unique=True
	)

	applicant = models.ForeignKey(
		User,
		on_delete=models.CASCADE,
		related_name="pass_applications",
		null=True,
		blank=True
	)

	pass_type = models.CharField(
		max_length=20,
		choices=PASS_TYPE_CHOICES
	)

	application_type = models.CharField(
		max_length=10,
		choices=APPLICATION_TYPE_CHOICES,
		default="NEW"
	)

	status = models.CharField(
		max_length=30,
		choices=STATUS_CHOICES,
		default="DRAFT"
	)

	verification_id = models.CharField(
		max_length=50,
		blank=True,
		null=True
	)

	disability_id = models.CharField(
		max_length=50,
		blank=True
	)

	staff_number = models.CharField(
		max_length=50,
		blank=True
	)

	full_name = models.CharField(max_length=150)
	registration_number = models.CharField(
		max_length=50,
		blank=True
	)

	college_name = models.CharField(
		max_length=200,
		blank=True
	)

	department = models.CharField(
		max_length=150,
		blank=True
	)

	date_of_birth = models.DateField(
		null=True,
		blank=True
	)

	phone_number = models.CharField(
		max_length=15,
		blank=True
	)

	address = models.TextField(
		blank=True
	)

	state = models.CharField(
		max_length=100,
		blank=True
	)

	district = models.CharField(
		max_length=100,
		blank=True
	)

	route = models.CharField(
		max_length=200,
		blank=True
	)

	start_point = models.CharField(
		max_length=150,
		blank=True
	)

	destination_point = models.CharField(
		max_length=150,
		blank=True
	)

	applicant_photo = models.FileField(
		upload_to="application_documents/photos/",
		blank=True,
		null=True,
		validators=[FileExtensionValidator(["jpg", "jpeg", "png"])]
	)

	aadhaar_document = models.FileField(
		upload_to="application_documents/aadhaar/",
		blank=True,
		null=True,
		validators=[FileExtensionValidator(["pdf"])]
	)

	signature_document = models.FileField(
		upload_to="application_documents/signatures/",
		blank=True,
		null=True,
		validators=[FileExtensionValidator(["pdf"])]
	)

	address_proof_document = models.FileField(
		upload_to="application_documents/address_proof/",
		blank=True,
		null=True,
		validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])]
	)

	staff_id_card_document = models.FileField(
		upload_to="application_documents/staff_id_cards/",
		blank=True,
		null=True,
		validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])]
	)

	remarks = models.TextField(
		blank=True
	)

	created_at = models.DateTimeField(
		auto_now_add=True
	)

	updated_at = models.DateTimeField(
		auto_now=True
	)

	def __str__(self):
		return f"{self.application_number} - {self.full_name}"


class EPass(models.Model):
	application = models.OneToOneField(
		PassApplication,
		on_delete=models.CASCADE,
		related_name="epass"
	)

	pass_number = models.CharField(
		max_length=50,
		unique=True
	)

	issue_date = models.DateField(
		auto_now_add=True
	)

	expiry_date = models.DateField()

	valid_from = models.DateField(null=True, blank=True)
	valid_until = models.DateField(null=True, blank=True)

	qr_data = models.TextField(
		blank=True
	)

	qr_code = models.FileField(
		upload_to="qr_codes/",
		blank=True,
		null=True
	)

	is_active = models.BooleanField(
		default=True
	)

	created_at = models.DateTimeField(
		auto_now_add=True
	)

	def __str__(self):
		return self.pass_number

	@property
	def renewal_valid_until(self):
		return self.valid_until or self.expiry_date

	@property
	def renewal_wait_days(self):
		return max(
			(self.renewal_valid_until - timezone.localdate()).days,
			0,
		)
