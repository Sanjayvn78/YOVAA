from django.contrib import admin
from .models import PassApplication


@admin.register(PassApplication)
class PassApplicationAdmin(admin.ModelAdmin):

	list_display = (
		"application_number",
		"full_name",
		"pass_type",
		"status",
		"verification_id",
		"created_at",
	)

	search_fields = (
		"application_number",
		"full_name",
		"verification_id",
	)

	list_filter = (
		"pass_type",
		"status",
	)
