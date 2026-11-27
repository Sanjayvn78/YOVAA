from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
	USER_TYPE_CHOICES = [
		("COLLEGE", "College Student"),
		("DISABLED", "Disabled Person"),
		("GENERAL", "General User"),
		("SPECIAL", "Special User"),
	]

	ROLE_CHOICES = [
		("USER", "User"),
		("SCHOOL_ADMIN", "School Admin"),
		("COLLEGE_ADMIN", "College Admin"),
		("TRANSPORT_ADMIN", "Transport Admin"),
		("CONDUCTOR", "Conductor"),
	]

	user = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		related_name="profile"
	)

	role = models.CharField(
		max_length=30,
		choices=ROLE_CHOICES,
		default="USER"
	)

	user_type = models.CharField(
		max_length=20,
		choices=USER_TYPE_CHOICES,
		default="GENERAL"
	)

	phone_number = models.CharField(
		max_length=15,
		blank=True
	)

	registration_number = models.CharField(max_length=50, blank=True)
	disability_id = models.CharField(max_length=50, blank=True)
	staff_number = models.CharField(max_length=50, blank=True)

	is_active = models.BooleanField(default=True)

	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return f"{self.user.username} - {self.role}"
