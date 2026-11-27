import uuid
import json
from pathlib import Path

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from passes.models import PassApplication
from payments.models import Payment
from verification.models import EMISStudent
from users.views import (
	COLLEGE_ROUTE_STOPS,
	calculate_pass_fee,
	generate_epass,
	valid_route_selection,
)


ADMIN_CREDENTIALS_PATH = Path(__file__).resolve().parent / "admin_credentials.json"
with ADMIN_CREDENTIALS_PATH.open(encoding="utf-8") as credentials_file:
	ADMIN_CREDENTIALS = json.load(credentials_file)

COLLEGE_ADMIN_ACCOUNTS = {
	item["username"]: item["institution"]
	for item in ADMIN_CREDENTIALS
	if item["type"] == "College"
}

SCHOOL_ADMIN_ACCOUNTS = {
	item["username"]: (item["institution"], item["state"])
	for item in ADMIN_CREDENTIALS
	if item["type"] == "School"
}

ADMIN_PASSWORDS = {
	item["username"]: item["password"]
	for item in ADMIN_CREDENTIALS
}


def _ensure_admin_account(username):
	user, _ = User.objects.get_or_create(username=username)
	if not user.check_password(ADMIN_PASSWORDS[username]):
		user.set_password(ADMIN_PASSWORDS[username])
		user.save(update_fields=["password"])
	return user


def _school_allowed_ids(username):
	school_name, state = SCHOOL_ADMIN_ACCOUNTS[username]
	students = EMISStudent.objects.filter(
		school_name=school_name,
		state=state,
	)
	if not students.exists():
		location = school_name.split(" Government")[0]
		location = location.split(" Matriculation")[0]
		location = location.split(" Public")[0]
		students = EMISStudent.objects.filter(
			school_name__istartswith=location,
			state=state,
		)
	return list(students.values_list("student_id", flat=True))


def _school_student_for_admin(student_id, allowed_ids):
	if not student_id:
		return None
	return EMISStudent.objects.filter(
		student_id=student_id,
		student_id__in=allowed_ids,
	).order_by("id").first()


def admin_login(request, admin_type):
	accounts = (
		COLLEGE_ADMIN_ACCOUNTS
		if admin_type == "college"
		else {username: details[0] for username, details in SCHOOL_ADMIN_ACCOUNTS.items()}
	)
	error = None
	if request.method == "POST":
		username = request.POST.get("username", "").strip()
		password = request.POST.get("password", "")
		if username not in accounts:
			error = "Invalid admin username or password."
		else:
			_ensure_admin_account(username)
			user = authenticate(request, username=username, password=password)
			if user is None:
				error = "Invalid admin username or password."
			else:
				login(request, user)
				request.session["admin_type"] = admin_type
				request.session["admin_username"] = username
				return redirect(
					"college_admin_dashboard"
					if admin_type == "college"
					else "school_admin"
				)
	return render(request, "admins/admin_login.html", {
		"admin_type": admin_type,
		"error": error,
	})


def admin_logout(request):
	logout(request)
	return redirect("admins_home")


def _admin_username(request, admin_type):
	username = request.session.get("admin_username")
	if not request.user.is_authenticated or request.session.get("admin_type") != admin_type:
		return None
	if admin_type == "college":
		return username if username in COLLEGE_ADMIN_ACCOUNTS else None
	return username if username in SCHOOL_ADMIN_ACCOUNTS else None


def admins_home(request):
	return render(request, "admins/home.html")


def school_admin(request):
	username = _admin_username(request, "school")
	if username is None:
		return redirect("school_admin_login")
	student_ids = _school_allowed_ids(username)
	applications = PassApplication.objects.filter(
		pass_type="SCHOOL",
		verification_id__in=student_ids,
	).order_by("-created_at")

	return render(
		request,
		"admins/school.html",
		{
			"admin_name": username,
			"school_name": SCHOOL_ADMIN_ACCOUNTS[username][0],
			"applications": applications,
			"pending_count": applications.filter(
				status="PAYMENT_PENDING"
			).count(),
			"epass_count": applications.filter(
				epass__isnull=False
			).count(),
		}
	)


def school_epass(request, application_id):
	username = _admin_username(request, "school")
	if username is None:
		return redirect("school_admin_login")
	allowed_ids = _school_allowed_ids(username)
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="SCHOOL",
		verification_id__in=allowed_ids,
		status="PAYMENT_COMPLETED",
	)
	pass_obj = getattr(application, "epass", None)
	if pass_obj is None:
		return redirect("school_admin")
	return render(
		request,
		"users/epass.html",
		{"application": application, "pass_obj": pass_obj},
	)


def school_apply(request):
	username = _admin_username(request, "school")
	if username is None:
		return redirect("school_admin_login")
	if request.method == "POST":
		student_id = request.POST.get("student_id")
		allowed_ids = _school_allowed_ids(username)
		student = _school_student_for_admin(student_id, allowed_ids)
		if student is not None:
			return render(
				request,
				"admins/school_verified.html",
				{"student": student}
			)
		return render(
			request,
			"admins/school_apply.html",
			{"error": "Student not found in EMIS dataset."}
		)

	return render(request, "admins/school_apply.html")


def school_application(request):
	username = _admin_username(request, "school")
	if username is None:
		return redirect("school_admin_login")
	student_id = request.GET.get("student_id")
	allowed_ids = _school_allowed_ids(username)

	student = _school_student_for_admin(student_id, allowed_ids)
	if student is None:
		return render(
			request,
			"admins/school_apply.html",
			{"error": "EMIS verification required."}
		)

	if request.method == "POST":
		route = request.POST.get("route")
		start_point = request.POST.get("start_point")
		destination_point = request.POST.get("destination_point")
		state = request.POST.get("state", "").strip()
		district = request.POST.get("district", "").strip()
		required_documents = {
			"applicant_photo": request.FILES.get("applicant_photo"),
			"staff_id_card_document": request.FILES.get("staff_id_card_document"),
			"aadhaar_document": request.FILES.get("aadhaar_document"),
		}
		missing_documents = [
			label for field, label in [
				("applicant_photo", "student photo"),
				("staff_id_card_document", "school ID"),
				("aadhaar_document", "Aadhaar document"),
			] if not required_documents[field]
		]
		if (
			not valid_route_selection(
				state, district, route, start_point, destination_point
			)
			or missing_documents
		):
			error = "Select a valid route and upload all required documents."
			if missing_documents:
				error += " Missing: " + ", ".join(missing_documents) + "."
			return render(
				request,
				"admins/school_application.html",
				{
					"student": student,
					"error": error,
				},
			)

		application = PassApplication.objects.create(
			application_number=(
				f"SCH-{student.student_id}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			pass_type="SCHOOL",
			status="PAYMENT_PENDING",
			verification_id=student.student_id,
			full_name=student.student_name,
			state=state,
			district=district,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
			applicant_photo=required_documents["applicant_photo"],
			staff_id_card_document=required_documents["staff_id_card_document"],
			aadhaar_document=required_documents["aadhaar_document"],
		)
		request.session["school_payment_application_id"] = application.id
		return redirect("payment", application_id=application.id)

	return render(
		request,
		"admins/school_application.html",
		{"student": student}
	)


def school_application_review(request, application_id):
	username = _admin_username(request, "school")
	if username is None:
		return redirect("school_admin_login")
	allowed_ids = _school_allowed_ids(username)
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="SCHOOL",
		verification_id__in=allowed_ids,
	)

	return render(
		request,
		"admins/school_application_review.html",
		{"application": application}
	)


def school_verify_application(request, application_id):
	username = _admin_username(request, "school")
	if username is None:
		return redirect("school_admin_login")
	allowed_ids = _school_allowed_ids(username)
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="SCHOOL",
		verification_id__in=allowed_ids,
	)

	if request.method == "POST":
		action = request.POST.get("action")
		remarks = request.POST.get("remarks")

		if action == "approve":
			application.status = "SCHOOL_APPROVED"
			application.remarks = remarks
			application.save()
		elif action == "reject":
			application.status = "SCHOOL_REJECTED"
			application.remarks = remarks
			application.save()

		return redirect("school_admin")

	return redirect(
		"school_application_review",
		application_id=application.id
	)


def college_admin(request):
	return redirect("college_admin_dashboard")


@login_required(login_url="/admin/login/")
def college_admin_dashboard(request):
	username = _admin_username(request, "college")
	if username is None:
		return redirect("college_admin_login")
	college_name = COLLEGE_ADMIN_ACCOUNTS[username]
	applications = PassApplication.objects.filter(
		pass_type="COLLEGE",
		college_name=college_name,
		status__in=["COLLEGE_VERIFICATION", "SUBMITTED"]
	).order_by("-created_at")

	return render(
		request,
		"admins/college_dashboard.html",
		{"applications": applications, "admin_name": username, "college_name": college_name}
	)


@login_required(login_url="/admin/login/")
def college_application_review(request, application_id):
	username = _admin_username(request, "college")
	if username is None:
		return redirect("college_admin_login")
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="COLLEGE",
		college_name=COLLEGE_ADMIN_ACCOUNTS[username],
	)

	return render(
		request,
		"admins/college_application_review.html",
		{"application": application}
	)


@login_required(login_url="/admin/login/")
def college_verify_application(request, application_id):
	username = _admin_username(request, "college")
	if username is None:
		return redirect("college_admin_login")
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="COLLEGE",
		college_name=COLLEGE_ADMIN_ACCOUNTS[username],
	)

	if request.method == "POST" and application.status in [
		"COLLEGE_VERIFICATION",
		"SUBMITTED",
	]:
		action = request.POST.get("action")
		remarks = request.POST.get("remarks", "").strip()

		if action == "approve":
			application.status = "COLLEGE_APPROVED"
			application.remarks = remarks
			application.save()
		elif action == "reject":
			application.status = "COLLEGE_REJECTED"
			application.remarks = remarks
			application.save()

		return redirect("college_admin_dashboard")

	return redirect(
		"college_application_review",
		application_id=application.id
	)


def transport_admin(request):
	applications = PassApplication.objects.all()
	general_payments = Payment.objects.filter(
		application__pass_type="GENERAL",
		status="PENDING",
		application__status="PAYMENT_PENDING",
	).select_related("application").order_by("created_at")
	return render(
		request,
		"admins/transport.html",
		{
			"general_payments": general_payments,
			"total_applications": applications.count(),
			"pending_applications": applications.filter(
				status__in=[
					"TRANSPORT_VERIFICATION",
					"COLLEGE_VERIFICATION",
					"SPECIAL_VERIFICATION",
					"PAYMENT_PENDING",
				]
			).count(),
			"generated_epasses": applications.filter(
				epass__isnull=False
			).count(),
			"school_count": applications.filter(pass_type="SCHOOL").count(),
			"college_count": applications.filter(pass_type="COLLEGE").count(),
			"disabled_count": applications.filter(pass_type="DISABLED").count(),
			"general_count": applications.filter(pass_type="GENERAL").count(),
			"special_count": applications.filter(pass_type="SPECIAL").count(),
		},
	)


def transport_school_portal(request):
	applications = PassApplication.objects.filter(
		pass_type="SCHOOL",
	).select_related("epass").order_by("-created_at")
	payments = Payment.objects.filter(
		application__pass_type="SCHOOL",
	).select_related("application").order_by("-created_at")
	return render(
		request,
		"admins/transport_school.html",
		{
			"applications": applications,
			"payments": payments,
			"active_section": request.GET.get("section", "applications"),
			"completed_count": applications.filter(
				status="PAYMENT_COMPLETED"
			).count(),
			"epass_count": applications.filter(
				epass__isnull=False
			).count(),
		},
	)


def transport_general_portal(request):
	applications = PassApplication.objects.filter(
		pass_type="GENERAL",
	).select_related("epass").order_by("-created_at")
	payments = Payment.objects.filter(
		application__pass_type="GENERAL",
	).select_related("application").order_by("-created_at")
	return render(
		request,
		"admins/transport_general.html",
		{
			"applications": applications,
			"payments": payments,
			"active_section": request.GET.get("section", "applications"),
			"pending_count": applications.filter(
				status="PAYMENT_PENDING"
			).count(),
			"paid_count": applications.filter(
				status="PAYMENT_COMPLETED"
			).count(),
			"fee": calculate_pass_fee(
				"",
				"",
				"",
				pass_type="GENERAL",
			),
		},
	)


def transport_college_portal(request):
	applications = PassApplication.objects.filter(
		pass_type="COLLEGE",
		status__in=[
			"TRANSPORT_VERIFICATION",
			"COLLEGE_VERIFICATION",
			"COLLEGE_APPROVED",
			"PAYMENT_PENDING",
			"PAYMENT_COMPLETED",
			"COLLEGE_REJECTED",
		]
	).order_by("-created_at")
	pending_statuses = ["TRANSPORT_VERIFICATION", "COLLEGE_VERIFICATION"]
	approved_statuses = [
		"COLLEGE_APPROVED",
		"PAYMENT_PENDING",
		"PAYMENT_COMPLETED",
	]
	paid_payments = Payment.objects.filter(
		application__pass_type="COLLEGE",
		status="SUCCESS",
	).select_related("application").order_by("-paid_at", "-created_at")
	approved_applications = applications.filter(
		status__in=approved_statuses
	)
	return render(
		request,
		"admins/transport_college.html",
		{
			"applications": applications,
			"active_section": request.GET.get("section", ""),
			"pending_count": applications.filter(
				status__in=pending_statuses
			).count(),
			"approved_count": applications.filter(
				status__in=approved_statuses
			).count(),
			"rejected_count": applications.filter(
				status="COLLEGE_REJECTED"
			).count(),
			"paid_payments": paid_payments,
			"approved_applications": approved_applications,
		},
	)


def transport_college_application_detail(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="COLLEGE",
	)
	return render(
		request,
		"admins/transport_college_application_detail.html",
		{"application": application},
	)


def transport_disabled_portal(request):
	applications = PassApplication.objects.filter(
		pass_type="DISABLED",
		status__in=["PAYMENT_PENDING", "PAYMENT_COMPLETED"],
	).order_by("-created_at")
	payments = Payment.objects.filter(
		application__pass_type="DISABLED",
	).select_related("application").order_by("-created_at")
	return render(
		request,
		"admins/transport_disabled.html",
		{
			"applications": applications,
			"payments": payments,
			"active_section": request.GET.get("section", "applications"),
			"pending_count": applications.filter(
				status="PAYMENT_PENDING"
			).count(),
			"paid_count": applications.filter(
				status="PAYMENT_COMPLETED"
			).count(),
		},
	)


def transport_special_portal(request):
	applications = PassApplication.objects.filter(
		pass_type="SPECIAL",
	).select_related("epass").order_by("-created_at")
	return render(
		request,
		"admins/transport_special.html",
		{
			"applications": applications,
			"pending_count": applications.filter(
				status="SPECIAL_VERIFICATION"
			).count(),
			"epass_count": applications.filter(
				epass__isnull=False
			).count(),
		},
	)


@login_required(login_url="/admin/login/")
def transport_verify_special_application(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="SPECIAL",
		status="SPECIAL_VERIFICATION",
	)
	if request.method == "POST":
		application.status = "APPROVED"
		application.save(update_fields=["status", "updated_at"])
		generate_epass(application)
	return redirect("transport_special_portal")


@login_required(login_url="/admin/login/")
def transport_send_college(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="COLLEGE",
		status="TRANSPORT_VERIFICATION",
	)
	if request.method == "POST":
		application.status = "COLLEGE_VERIFICATION"
		application.remarks = request.POST.get("remarks", "").strip()
		application.save()
	return redirect("transport_college_portal")


@login_required(login_url="/admin/login/")
def transport_allow_payment(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="COLLEGE",
		status="COLLEGE_APPROVED",
	)
	if request.method == "POST":
		application.status = "PAYMENT_PENDING"
		application.remarks = request.POST.get("remarks", "").strip()
		application.save()
	return redirect("transport_college_portal")


@login_required(login_url="/admin/login/")
def transport_verify_general_payment(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type="GENERAL",
		status="PAYMENT_PENDING",
	)
	payment = get_object_or_404(
		Payment,
		application=application,
		status="PENDING",
	)
	if request.method == "POST":
		payment.transaction_id = (
			"YOVAA-" + uuid.uuid4().hex[:10].upper()
		)
		payment.status = "SUCCESS"
		payment.paid_at = timezone.now()
		payment.save()
		application.status = "PAYMENT_COMPLETED"
		application.save(update_fields=["status", "updated_at"])
		generate_epass(application)
	return redirect("transport_admin")


@login_required(login_url="/admin/login/")
def transport_verify_payment(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		pass_type__in=["COLLEGE", "SCHOOL", "DISABLED"],
		status="PAYMENT_PENDING",
	)
	payment = get_object_or_404(
		Payment,
		application=application,
		status="PENDING",
	)
	if request.method == "POST":
		payment.transaction_id = "YOVAA-" + uuid.uuid4().hex[:10].upper()
		payment.status = "SUCCESS"
		payment.paid_at = timezone.now()
		payment.save()
		application.status = "PAYMENT_COMPLETED"
		application.save(update_fields=["status", "updated_at"])
		generate_epass(application)
	if application.pass_type == "COLLEGE":
		return redirect("transport_college_portal")
	return redirect(
		"transport_school_portal"
		if application.pass_type == "SCHOOL"
		else "transport_disabled_portal"
	)


