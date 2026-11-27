from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = (
		"application",
		"transaction_id",
		"amount",
		"status",
		"paid_at",
		"created_at",
	)
	search_fields = ("application__application_number", "transaction_id")
	list_filter = ("status",)
