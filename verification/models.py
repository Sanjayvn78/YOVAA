from django.db import models

class UMISStudent(models.Model):
	umis_number = models.CharField(
		max_length=50,
		blank=True,
		null=True,
	)
	registration_number = models.CharField(max_length=50)
	name = models.CharField(max_length=150)
	college_name = models.CharField(max_length=200)
	department = models.CharField(max_length=150)
	course = models.CharField(max_length=150)
	year = models.CharField(max_length=20)
	date_of_birth = models.DateField(null=True, blank=True)
	college_address = models.TextField(blank=True)
	academic_year = models.CharField(max_length=20)
	state = models.CharField(max_length=100, blank=True)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.registration_number} - {self.name}"

class EMISStudent(models.Model):
	student_id = models.CharField(max_length=50)
	student_name = models.CharField(max_length=150)
	school_name = models.CharField(max_length=200)
	class_name = models.CharField(max_length=50)
	academic_year = models.CharField(max_length=20)
	state = models.CharField(max_length=100, blank=True)
	student_status = models.CharField(max_length=30, default="Active")

	def __str__(self):
		return f"{self.student_id} - {self.student_name}"

class DisabledPerson(models.Model):
	disability_id = models.CharField(max_length=50)
	name = models.CharField(max_length=150)
	date_of_birth = models.DateField(null=True, blank=True)
	disability_type = models.CharField(max_length=150)
	disability_percentage = models.PositiveIntegerField(
		null=True,
		blank=True
	)
	address = models.TextField(blank=True)
	district = models.CharField(max_length=100, blank=True)
	state = models.CharField(max_length=100, blank=True)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.disability_id} - {self.name}"

class GovernmentTransportStaff(models.Model):
	staff_number = models.CharField(max_length=50)
	name = models.CharField(max_length=150)
	date_of_birth = models.DateField(null=True, blank=True)
	department = models.CharField(max_length=150)
	designation = models.CharField(max_length=150)
	workplace = models.CharField(max_length=200)
	district = models.CharField(max_length=100, blank=True)
	state = models.CharField(max_length=100, blank=True)
	employment_status = models.CharField(max_length=50, default="ACTIVE")
	is_eligible = models.BooleanField(default=True)
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.staff_number} - {self.name}"
