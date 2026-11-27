from django.contrib import admin
from .models import (
    UMISStudent,
    EMISStudent,
    DisabledPerson,
    GovernmentTransportStaff,
)


@admin.register(UMISStudent)
class UMISStudentAdmin(admin.ModelAdmin):
    list_display = (
        "registration_number",
        "name",
        "college_name",
        "department",
        "year",
        "academic_year",
        "is_active",
    )
    search_fields = (
        "registration_number",
        "name",
        "college_name",
    )
    list_filter = ("is_active", "academic_year")


@admin.register(EMISStudent)
class EMISStudentAdmin(admin.ModelAdmin):
    list_display = (
        "student_id",
        "student_name",
        "school_name",
        "class_name",
        "academic_year",
        "student_status",
    )
    search_fields = (
        "student_id",
        "student_name",
        "school_name",
    )
    list_filter = ("student_status", "academic_year")


@admin.register(DisabledPerson)
class DisabledPersonAdmin(admin.ModelAdmin):
    list_display = (
        "disability_id",
        "name",
        "date_of_birth",
        "disability_type",
        "district",
        "is_active",
    )
    search_fields = (
        "disability_id",
        "name",
    )
    list_filter = ("is_active", "disability_type", "district")


@admin.register(GovernmentTransportStaff)
class GovernmentTransportStaffAdmin(admin.ModelAdmin):
    list_display = (
        "staff_number",
        "name",
        "department",
        "designation",
        "workplace",
        "district",
        "employment_status",
        "is_eligible",
    )
    search_fields = (
        "staff_number",
        "name",
    )
    list_filter = (
        "employment_status",
        "is_eligible",
    )