from django.db import models
from passes.models import PassApplication


class Payment(models.Model):
	PAYMENT_METHOD_CHOICES = [
		("UPI", "UPI"),
		("QR", "QR Code"),
	]

	STATUS_CHOICES = [
		("PENDING", "Pending"),
		("SUCCESS", "Success"),
		("FAILED", "Failed"),
	]

	application = models.OneToOneField(
		PassApplication,
		on_delete=models.CASCADE,
		related_name="payment"
	)

	transaction_id = models.CharField(
		max_length=100,
		unique=True,
		blank=True,
		null=True
	)

	amount = models.DecimalField(max_digits=10, decimal_places=2)
	payment_method = models.CharField(
		max_length=10,
		choices=PAYMENT_METHOD_CHOICES,
		default="UPI",
	)
	status = models.CharField(
		max_length=30,
		choices=STATUS_CHOICES,
		default="PENDING"
	)
	paid_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	def __str__(self):
		return self.application.application_number
