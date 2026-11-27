import base64
from datetime import date, timedelta
from io import BytesIO
import uuid
import json
from mimetypes import guess_type
from pathlib import Path

from django.core.files import File
from django.db.models import Q
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from passes.models import EPass, PassApplication
from payments.models import Payment
from verification.models import (
	DisabledPerson,
	GovernmentTransportStaff,
	EMISStudent,
	UMISStudent,
)


ROUTE_CATALOG_PATH = Path(__file__).resolve().parent.parent / "routes/route_catalog.json"
with ROUTE_CATALOG_PATH.open(encoding="utf-8") as route_file:
	ROUTE_NETWORK = json.load(route_file)

COLLEGE_ROUTE_STOPS = ROUTE_NETWORK.get("Tamil Nadu", {}).get("Coimbatore", {})


def route_stops_for_selection(state, district, route):
	return ROUTE_NETWORK.get(state, {}).get(district, {}).get(route, [])


def valid_route_selection(state, district, route, start_point, destination_point):
	stops = route_stops_for_selection(state, district, route)
	return bool(
		stops
		and start_point in stops
		and destination_point in stops
		and start_point != destination_point
	)


def disabled_application_exists_this_month(disability_id):
	today = timezone.localdate()
	return PassApplication.objects.filter(
		pass_type="DISABLED",
		disability_id=disability_id,
		created_at__year=today.year,
		created_at__month=today.month,
	).exists()


ACTIVE_PASS_STATUSES = {
	"COLLEGE_VERIFICATION",
	"SCHOOL_VERIFICATION",
	"DISABLED_VERIFICATION",
	"GENERAL_VERIFICATION",
	"SPECIAL_VERIFICATION",
	"TRANSPORT_VERIFICATION",
	"PAYMENT_PENDING",
	"PAYMENT_COMPLETED",
	"COLLEGE_APPROVED",
	"SCHOOL_APPROVED",
	"APPROVED",
}


def user_has_pass_this_month(user):
	if not user or not user.is_authenticated:
		return False
	today = timezone.localdate()
	return PassApplication.objects.filter(
		applicant=user,
		created_at__year=today.year,
		created_at__month=today.month,
		status__in=sorted(ACTIVE_PASS_STATUSES),
	).exists()


def registration_has_pass_this_month(registration_number):
	today = timezone.localdate()
	return PassApplication.objects.filter(
		pass_type="COLLEGE",
		registration_number=registration_number,
		created_at__year=today.year,
		created_at__month=today.month,
		status__in=sorted(ACTIVE_PASS_STATUSES),
	).exists()


def student_has_existing_college_pass(registration_number):
	return PassApplication.objects.filter(
		pass_type="COLLEGE",
		registration_number__iexact=registration_number,
		status__in=sorted(ACTIVE_PASS_STATUSES),
	).exists()


def calculate_pass_fee(
	route,
	start_point,
	destination_point,
	pass_type=None,
	application_type="NEW",
):
	if pass_type == "SCHOOL":
		return 30.00
	if pass_type == "DISABLED":
		return 550.00
	if pass_type == "GENERAL":
		return 1100.00

	stops = COLLEGE_ROUTE_STOPS.get(route, [])
	if not stops:
		return 200.00
	try:
		start_index = stops.index(start_point)
		destination_index = stops.index(destination_point)
	except ValueError:
		return 200.00
	stop_difference = abs(destination_index - start_index)
	return round(200 + (stop_difference * 30), 2)


def users_home(request):
	return render(request, "users/home.html")


def college_apply(request):
	if request.method == "POST":
		registration_number = (request.POST.get("registration_number") or "").strip()
		if not registration_number:
			return render(
				request,
				"users/college_pass.html",
				{"error": "Enter a valid registration number."},
			)

		student = UMISStudent.objects.filter(
			registration_number__iexact=registration_number,
			is_active=True,
		).first()
		if student is None:
			return render(
				request,
				"users/college_pass.html",
				{"error": "Student not found in UMIS dataset."},
			)

		if student_has_existing_college_pass(student.registration_number):
			return render(
				request,
				"users/college_pass.html",
				{
					"error": (
						"This UMIS student already has a college pass active or under process. "
						"One pass per student is allowed."
					),
				},
			)

		return render(
			request,
			"users/college_verified.html",
			{"student": student},
		)

	return render(request, "users/college_pass.html")


@login_required(login_url="/accounts/login/college/")
def college_details(request):
	student_id = request.POST.get("student_id") or request.GET.get("student_id")
	student = None
	if student_id:
		student = get_object_or_404(UMISStudent, id=student_id, is_active=True)
	elif request.method == "GET":
		return redirect("college_apply")

	if request.method == "POST":
		if student is None:
			student = get_object_or_404(UMISStudent, id=request.POST.get("student_id"), is_active=True)
		if student_has_existing_college_pass(student.registration_number):
			return render(
				request,
				"users/college_details.html",
				{
					"student": student,
					"error": (
						"This UMIS student already has a college pass active or under process. "
						"One pass per student is allowed."
					),
				},
			)

		state = (request.POST.get("state") or "").strip() or student.state
		district = (request.POST.get("district") or "").strip()
		route = (request.POST.get("route") or "").strip()
		start_point = (request.POST.get("start_point") or "").strip()
		destination_point = (request.POST.get("destination_point") or "").strip()
		if not valid_route_selection(state, district, route, start_point, destination_point):
			return render(
				request,
				"users/college_details.html",
				{
					"student": student,
					"error": "Select a valid route and boarding/destination stop.",
				},
			)

		application = PassApplication.objects.create(
			application_number=f"COL-{student.registration_number}-{uuid.uuid4().hex[:6].upper()}",
			applicant=request.user,
			pass_type="COLLEGE",
			application_type="NEW",
			status="PAYMENT_PENDING",
			verification_id=student.registration_number,
			full_name=student.name,
			registration_number=student.registration_number,
			college_name=student.college_name,
			department=student.department,
			date_of_birth=student.date_of_birth,
			address=student.college_address,
			state=state,
			district=district,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
			applicant_photo=request.FILES.get("applicant_photo"),
			aadhaar_document=request.FILES.get("aadhaar_document"),
			signature_document=request.FILES.get("signature_document"),
		)
		return redirect("payment", application_id=application.id)

	return render(
		request,
		"users/college_details.html",
		{"student": student},
	)


def disabled_apply(request):
	if request.method == "POST":
		disability_id = request.POST.get("disability_id")
		person = DisabledPerson.objects.filter(
			disability_id=disability_id,
			is_active=True
		).first()

		if person is None:
			return render(
				request,
				"users/disabled_apply.html",
				{"error": "Disability ID not found."}
			)

		return render(
			request,
			"users/disabled_verified.html",
			{"person": person}
		)

	return render(request, "users/disabled_apply.html")


@login_required(login_url="/admin/login/")
def disabled_pass(request):
	person = None
	error = None

	if request.method == "POST":
		person = DisabledPerson.objects.filter(
			disability_id=request.POST.get("disability_id"),
			is_active=True
		).first()
		if person is None:
			error = "Disability ID not found in the verification dataset."

	return render(
		request,
		"users/disabled_pass.html",
		{"person": person, "error": error}
	)


@login_required(login_url="/admin/login/")
def create_disabled_application(request, person_id):
	person = get_object_or_404(
		DisabledPerson,
		id=person_id,
		is_active=True
	)

	if request.method == "POST":
		if disabled_application_exists_this_month(person.disability_id):
			return render(
				request,
				"users/create_disabled_application.html",
				{
					"person": person,
					"error": (
						"This person already has a disabled pass application "
						"for this month."
					),
				},
			)
		state = request.POST.get("state", "").strip() or person.state
		district = request.POST.get("district", "").strip() or person.district
		if not district:
			return render(
				request,
				"users/create_disabled_application.html",
				{
					"person": person,
					"error": "A valid travel district is required.",
				},
			)

		application = PassApplication.objects.create(
			application_number=(
				f"DIS-{person.disability_id}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			applicant=request.user,
			pass_type="DISABLED",
			application_type="NEW",
			status="PAYMENT_PENDING",
			verification_id=person.disability_id,
			disability_id=person.disability_id,
			full_name=person.name,
			date_of_birth=person.date_of_birth,
			address=person.address,
			state=state,
			district=district,
			applicant_photo=request.FILES.get("applicant_photo"),
			aadhaar_document=request.FILES.get("aadhaar_document"),
			signature_document=request.FILES.get("signature_document"),
		)
		return redirect(
			"payment",
			application_id=application.id,
		)

	return render(
		request,
		"users/create_disabled_application.html",
		{"person": person}
	)


def disabled_details(request):
	if request.method != "POST":
		return redirect("disabled_apply")

	person = get_object_or_404(
		DisabledPerson,
		id=request.POST.get("person_id"),
		is_active=True
	)

	if request.POST.get("district") or person.district:
		if disabled_application_exists_this_month(person.disability_id):
			return render(
				request,
				"users/disabled_details.html",
				{
					"person": person,
					"error": (
						"This person already has a disabled pass application "
						"for this month."
					),
				},
			)
		state = request.POST.get("state", "").strip() or person.state
		district = request.POST.get("district", "").strip() or person.district

		application = PassApplication.objects.create(
			application_number=(
				f"DIS-{person.disability_id}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			applicant=(request.user if request.user.is_authenticated else None),
			pass_type="DISABLED",
			application_type="NEW",
			status="PAYMENT_PENDING",
			verification_id=person.disability_id,
			disability_id=person.disability_id,
			full_name=person.name,
			date_of_birth=person.date_of_birth,
			address=person.address,
			state=state,
			district=district,
			applicant_photo=request.FILES.get("applicant_photo"),
			aadhaar_document=request.FILES.get("aadhaar_document"),
			signature_document=request.FILES.get("signature_document"),
		)
		return redirect("payment", application_id=application.id)

	return render(request, "users/disabled_details.html", {"person": person})


def special_apply(request):
	return redirect("special_login")


def special_details(request):
	if request.method != "POST":
		return redirect("special_apply")

	staff = get_object_or_404(
		GovernmentTransportStaff,
		id=request.POST.get("staff_id"),
		is_active=True,
		is_eligible=True,
		employment_status__iexact="ACTIVE"
	)

	if request.POST.get("submit_application"):
		application = PassApplication.objects.create(
			application_number=(
				f"SPC-{staff.staff_number}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			applicant=(request.user if request.user.is_authenticated else None),
			pass_type="SPECIAL",
			application_type="NEW",
			status="SPECIAL_VERIFICATION",
			verification_id=staff.staff_number,
			full_name=staff.name,
			staff_number=staff.staff_number,
		)
		return render(
			request,
			"users/application_success.html",
			{"application": application}
		)

	return render(request, "users/special_details.html", {"staff": staff})


@login_required(login_url="/accounts/login/general/")
def general_apply(request):
	monthly_limit_error = None
	if user_has_pass_this_month(request.user):
		monthly_limit_error = "You can purchase only one bus pass per month. Your current month's pass is already active or processing."

	if monthly_limit_error:
		return render(
			request,
			"users/general_apply.html",
			{"error": monthly_limit_error},
		)

	if request.method == "POST":
		request.session["general_details"] = {
			"full_name": request.POST.get("full_name"),
			"date_of_birth": request.POST.get("date_of_birth"),
			"phone_number": request.POST.get("phone_number"),
			"address": request.POST.get("address"),
		}
		return redirect("general_travel")

	return render(request, "users/general_apply.html")


@login_required(login_url="/accounts/login/general/")
def general_travel(request):
	details = request.session.get("general_details")
	if not details:
		return redirect("general_apply")

	if request.method == "POST":
		if user_has_pass_this_month(request.user):
			return render(
				request,
				"users/general_travel.html",
				{
					"error": "You can purchase only one bus pass per month. Your current month's pass is already active or processing.",
				},
			)
		route = request.POST.get("route")
		start_point = request.POST.get("start_point")
		destination_point = request.POST.get("destination_point")
		state = request.POST.get("state", "").strip()
		district = request.POST.get("district", "").strip()
		if (
			not valid_route_selection(
				state, district, route, start_point, destination_point
			)
		):
			return render(
				request,
				"users/general_travel.html",
				{
					"error": "Select a valid route and boarding/destination stop.",
				},
			)

		application = PassApplication.objects.create(
			application_number=f"GEN-{uuid.uuid4().hex[:10].upper()}",
			applicant=(request.user if request.user.is_authenticated else None),
			pass_type="GENERAL",
			application_type="NEW",
			status="PAYMENT_PENDING",
			full_name=details["full_name"],
			date_of_birth=details["date_of_birth"],
			phone_number=details["phone_number"],
			address=details["address"],
			state=state,
			district=district,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
			applicant_photo=request.FILES.get("applicant_photo"),
			aadhaar_document=request.FILES.get("aadhaar_document"),
			signature_document=request.FILES.get("signature_document"),
		)
		request.session.pop("general_details", None)
		return redirect(
			"payment",
			application_id=application.id,
		)

	return render(request, "users/general_travel.html")


def generate_epass(application):
	import qrcode

	issue_date = date.today()
	qr_expiry_date = issue_date + timedelta(days=365)
	epass_expiry_date = issue_date + timedelta(days=30)
	pass_number = "YOVAA-" + str(uuid.uuid4())[:8].upper()
	qr_data = pass_number
	valid_until = issue_date + timedelta(
		days=365 if application.pass_type == "SCHOOL" else 30
	)
	ep_pass = EPass.objects.create(
		application=application,
		pass_number=pass_number,
		expiry_date=qr_expiry_date,
		valid_from=issue_date,
		valid_until=valid_until,
		qr_data=qr_data
	)
	qr_buffer = BytesIO()
	qrcode.make(qr_data).save(qr_buffer, format="PNG")
	ep_pass.qr_code.save(
		f"{pass_number}.png",
		File(qr_buffer),
		save=True
	)
	return ep_pass


def ensure_epass_qr(ep_pass):
	import qrcode

	if ep_pass.valid_from is None:
		ep_pass.valid_from = ep_pass.issue_date
	if ep_pass.valid_until is None:
		ep_pass.valid_until = ep_pass.expiry_date
	if not ep_pass.qr_code:
		qr_data = ep_pass.pass_number
		ep_pass.qr_data = qr_data
		qr_buffer = BytesIO()
		qrcode.make(qr_data).save(qr_buffer, format="PNG")
		ep_pass.qr_code.save(
			f"{ep_pass.pass_number}.png",
			File(qr_buffer),
			save=False
		)
	ep_pass.save()
	return ep_pass


def college_pass(request):
	if request.method == "POST":
		registration_number = request.POST.get("registration_number")

		try:
			student = UMISStudent.objects.get(
				registration_number=registration_number,
				is_active=True
			)
			return render(
				request,
				"users/college_verified.html",
				{"student": student}
			)
		except UMISStudent.DoesNotExist:
			return render(
				request,
				"users/college_pass.html",
				{"error": "Student not found in UMIS dataset."}
			)

	return render(request, "users/college_pass.html")


def college_application(request):
	registration_number = request.GET.get("registration_number")

	try:
		student = UMISStudent.objects.get(
			registration_number=registration_number,
			is_active=True
		)
	except UMISStudent.DoesNotExist:
		return render(
			request,
			"users/college_pass.html",
			{"error": "UMIS verification required."}
		)

	if request.method == "POST":
		route = request.POST.get("route")
		start_point = request.POST.get("start_point")
		destination_point = request.POST.get("destination_point")

		application = PassApplication.objects.create(
			application_number=f"COL-{student.registration_number}",
			applicant=(request.user if request.user.is_authenticated else None),
			pass_type="COLLEGE",
			status="COLLEGE_VERIFICATION",
			verification_id=student.registration_number,
			full_name=student.name,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
		)

		return render(
			request,
			"users/application_success.html",
			{"application": application}
		)

	return render(
		request,
		"users/college_application.html",
		{"student": student}
	)


def disabled_application(request):
	disability_id = request.GET.get("disability_id")

	try:
		person = DisabledPerson.objects.get(
			disability_id=disability_id
		)
	except DisabledPerson.DoesNotExist:
		return render(
			request,
			"users/disabled_pass.html",
			{"error": "Disability verification required."}
		)

	if request.method == "POST":
		route = request.POST.get("route")
		start_point = request.POST.get("start_point")
		destination_point = request.POST.get("destination_point")

		application = PassApplication.objects.create(
			application_number=f"DIS-{person.disability_id}",
			applicant=(request.user if request.user.is_authenticated else None),
			pass_type="DISABLED",
			status="DISABLED_VERIFICATION",
			verification_id=person.disability_id,
			full_name=person.name,
			disability_id=person.disability_id,
			date_of_birth=person.date_of_birth,
			address=person.address,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
		)

		return render(
			request,
			"users/application_success.html",
			{"application": application}
		)

	return render(
		request,
		"users/disabled_application.html",
		{"person": person}
	)


@login_required(login_url="/accounts/login/general/")
def general_pass(request):
	if request.method == "POST":
		route = request.POST.get("route")
		start_point = request.POST.get("start_point")
		destination_point = request.POST.get("destination_point")
		state = request.POST.get("state", "").strip()
		district = request.POST.get("district", "").strip()
		if (
			not valid_route_selection(
				state, district, route, start_point, destination_point
			)
		):
			return render(
				request,
				"users/general_pass.html",
				{"error": "Select a valid route and boarding/destination stop."},
			)

		application = PassApplication.objects.create(
			application_number=f"GEN-{uuid.uuid4().hex[:10].upper()}",
			applicant=request.user,
			pass_type="GENERAL",
			application_type="NEW",
			status="PAYMENT_PENDING",
			full_name=request.POST.get("full_name"),
			date_of_birth=request.POST.get("date_of_birth"),
			phone_number=request.POST.get("phone_number"),
			address=request.POST.get("address", "").strip(),
			state=state,
			district=district,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
			applicant_photo=request.FILES.get("applicant_photo"),
			aadhaar_document=request.FILES.get("aadhaar_document"),
			signature_document=request.FILES.get("signature_document"),
		)
		return redirect(
			"payment",
			application_id=application.id,
		)

	return render(request, "users/general_pass.html")


@login_required(login_url="/admin/login/")
def special_pass(request):
	staff = None
	error = None

	if request.method == "POST":
		staff = GovernmentTransportStaff.objects.filter(
			staff_number=request.POST.get("staff_number"),
			employment_status__iexact="ACTIVE",
			is_eligible=True,
			is_active=True
		).first()
		if staff is None:
			error = "Staff number not found or staff is not eligible."

	return render(
		request,
		"users/special_pass.html",
		{"staff": staff, "error": error}
	)


@login_required(login_url="/admin/login/")
def create_special_application(request, staff_id):
	staff = get_object_or_404(
		GovernmentTransportStaff,
		id=staff_id,
		employment_status__iexact="ACTIVE",
		is_eligible=True,
		is_active=True
	)

	if request.method == "POST":
		application = PassApplication.objects.create(
			application_number=(
				f"SPC-{staff.staff_number}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			applicant=request.user,
			pass_type="SPECIAL",
			application_type="NEW",
			status="SPECIAL_VERIFICATION",
			verification_id=staff.staff_number,
			staff_number=staff.staff_number,
			full_name=staff.name,
			date_of_birth=staff.date_of_birth,
			route=request.POST.get("route"),
			start_point=request.POST.get("start_point"),
			destination_point=request.POST.get("destination_point"),
		)
		return redirect(
			"user_application_detail",
			application_id=application.id
		)

	return render(
		request,
		"users/create_special_application.html",
		{"staff": staff}
	)


def special_application(request):
	staff_number = request.GET.get("staff_number")

	try:
		staff = GovernmentTransportStaff.objects.get(
			staff_number=staff_number
		)
	except GovernmentTransportStaff.DoesNotExist:
		return render(
			request,
			"users/special_pass.html",
			{"error": "Staff verification required."}
		)

	if not staff.is_eligible or not staff.is_active:
		return render(
			request,
			"users/special_pass.html",
			{"error": "Staff is not eligible for free travel."}
		)

	if request.method == "POST":
		route = request.POST.get("route")
		start_point = request.POST.get("start_point")
		destination_point = request.POST.get("destination_point")

		application = PassApplication.objects.create(
			application_number=f"SPC-{staff.staff_number}",
			applicant=(request.user if request.user.is_authenticated else None),
			pass_type="SPECIAL",
			status="SPECIAL_VERIFICATION",
			verification_id=staff.staff_number,
			full_name=staff.name,
			staff_number=staff.staff_number,
			route=route,
			start_point=start_point,
			destination_point=destination_point,
		)

		return render(
			request,
			"users/application_success.html",
			{"application": application}
		)

	return render(
		request,
		"users/special_application.html",
		{"staff": staff}
	)


@login_required(login_url="/accounts/login/general/")
def user_dashboard(request):
	profile = getattr(request.user, "profile", None)
	if profile is not None:
		dashboard_routes = {
			"COLLEGE": "college_dashboard",
			"DISABLED": "disabled_dashboard",
			"GENERAL": "general_dashboard",
			"SPECIAL": "special_dashboard",
		}
		dashboard_route = dashboard_routes.get(profile.user_type)
		if dashboard_route:
			return redirect(dashboard_route)

	applications = PassApplication.objects.filter(
		applicant=request.user
	).order_by("-created_at")

	return render(
		request,
		"users/dashboard.html",
		{"applications": applications}
	)


def admin_dashboard(request):
	return render(request, "users/admin_dashboard.html")


@login_required(login_url="/admin/login/")
def conductor_dashboard(request):
	profile = getattr(request.user, "profile", None)
	if profile is None or profile.role != "CONDUCTOR":
		return redirect("admin_dashboard")

	return render(request, "users/conductor_dashboard.html")


@login_required(login_url="/admin/login/")
def school_admin(request):
	student = None
	error = None

	if request.method == "POST":
		student = EMISStudent.objects.filter(
			student_id=request.POST.get("student_id"),
			student_status="Active"
		).first()
		if student is None:
			error = "Student not found in EMIS dataset."

	return render(
		request,
		"users/school_admin.html",
		{"student": student, "error": error}
	)


@login_required(login_url="/admin/login/")
def college_admin(request):
	student = None
	error = None

	if request.method == "POST":
		student = UMISStudent.objects.filter(
			registration_number=request.POST.get("registration_number"),
			is_active=True
		).first()
		if student is None:
			error = "Student not found in UMIS dataset."

	return render(
		request,
		"users/college_admin.html",
		{"student": student, "error": error}
	)


@login_required(login_url="/admin/login/")
def create_college_pass(request, student_id):
	student = get_object_or_404(
		UMISStudent,
		id=student_id,
		is_active=True
	)

	if request.method == "POST":
		if student_has_existing_college_pass(student.registration_number):
			return render(
				request,
				"users/college_admin.html",
				{"student": student, "error": "This UMIS student already has a college pass active or under process. One pass per student is allowed."},
			)
		application = PassApplication.objects.create(
			application_number=(
				f"COL-{student.registration_number}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			applicant=request.user,
			pass_type="COLLEGE",
			application_type="NEW",
			status="COLLEGE_VERIFICATION",
			verification_id=student.registration_number,
			full_name=student.name,
			registration_number=student.registration_number,
			college_name=student.college_name,
			department=student.department,
			date_of_birth=student.date_of_birth,
			address=student.college_address,
			route=request.POST.get("route"),
			start_point=request.POST.get("start_point"),
			destination_point=request.POST.get("destination_point"),
		)
		return render(
			request,
			"users/application_success.html",
			{"application": application}
		)

	return render(
		request,
		"users/create_college_pass.html",
		{"student": student}
	)


@login_required(login_url="/admin/login/")
def create_school_pass(request, student_id):
	student = get_object_or_404(
		EMISStudent,
		id=student_id,
		student_status="Active"
	)

	if request.method == "POST":
		application = PassApplication.objects.create(
			application_number=(
				f"SCH-{student.student_id}-"
				f"{uuid.uuid4().hex[:6].upper()}"
			),
			applicant=request.user,
			pass_type="SCHOOL",
			application_type="NEW",
			status="SCHOOL_VERIFICATION",
			verification_id=student.student_id,
			full_name=student.student_name,
			route=request.POST.get("route"),
			start_point=request.POST.get("start_point"),
			destination_point=request.POST.get("destination_point"),
			applicant_photo=request.FILES.get("applicant_photo"),
			aadhaar_document=request.FILES.get("aadhaar_document"),
			signature_document=request.FILES.get("signature_document"),
		)
		return render(
			request,
			"users/application_success.html",
			{"application": application}
		)

	return render(
		request,
		"users/create_school_pass.html",
		{"student": student}
	)


@login_required(login_url="/admin/login/")
def user_application_detail(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		applicant=request.user
	)

	return render(
		request,
		"users/application_detail.html",
		{"application": application}
	)


@login_required(login_url="/accounts/login/college/")
def renew_pass(request, application_id):
	return redirect("user_dashboard")


def payment(request, application_id):
	application_query = PassApplication.objects.filter(
		id=application_id,
		status="PAYMENT_PENDING",
	)
	if request.user.is_authenticated:
		application_query = application_query.filter(
			Q(applicant=request.user) | Q(pass_type="SCHOOL")
		)
	else:
		application_query = application_query.filter(
			pass_type="SCHOOL",
			id=request.session.get("school_payment_application_id"),
		)
	application = get_object_or_404(application_query)
	amount = calculate_pass_fee(
		application.route,
		application.start_point,
		application.destination_point,
		pass_type=application.pass_type,
		application_type=application.application_type,
	)
	payment_record, _ = Payment.objects.get_or_create(
		application=application,
		defaults={"amount": amount}
	)
	if payment_record.amount != amount:
		payment_record.amount = amount
		payment_record.save(update_fields=["amount"])

	if request.method == "POST":
		payment_method = request.POST.get("payment_method", "UPI")
		if payment_method not in {"UPI", "QR"}:
			payment_method = "UPI"
		payment_record.payment_method = payment_method
		payment_record.status = "PENDING"
		payment_record.save(update_fields=["payment_method", "status"])
		return redirect(
			"payment_verify",
			application_id=application.id,
		)

	return render(
		request,
		"users/payment.html",
		{"application": application, "payment": payment_record}
	)


def payment_verify(request, application_id):
	application_query = PassApplication.objects.filter(
		id=application_id,
		status__in=["PAYMENT_PENDING", "PAYMENT_COMPLETED"],
	)
	if request.user.is_authenticated:
		application_query = application_query.filter(
			Q(applicant=request.user) | Q(pass_type="SCHOOL")
		)
	else:
		application_query = application_query.filter(
			pass_type="SCHOOL",
			id=request.session.get("school_payment_application_id"),
		)
	application = get_object_or_404(application_query)
	if application.status == "PAYMENT_COMPLETED":
		return redirect(
			"payment_success",
			application_id=application.id,
		)
	if application.status != "PAYMENT_PENDING":
		return render(
			request,
			"users/payment_verify.html",
			{
				"application": application,
				"payment": getattr(application, "payment", None),
				"message": "This application is not awaiting payment verification.",
			},
		)
	payment_record = get_object_or_404(
		Payment,
		application=application,
		status="PENDING",
	)
	return render(
		request,
		"users/payment_verify.html",
		{"application": application, "payment": payment_record},
	)


def payment_success(request, application_id):
	application_query = PassApplication.objects.filter(
		id=application_id,
		status="PAYMENT_COMPLETED",
	)
	if request.user.is_authenticated:
		application_query = application_query.filter(
			Q(applicant=request.user) | Q(pass_type="SCHOOL")
		)
	else:
		application_query = application_query.filter(
			pass_type="SCHOOL",
			id=request.session.get("school_payment_application_id"),
		)
	application = get_object_or_404(application_query)
	payment_record = get_object_or_404(
		Payment,
		application=application,
		status="SUCCESS"
	)

	return render(
		request,
		"users/payment_success.html",
		{"application": application, "payment": payment_record}
	)


@login_required(login_url="/accounts/login/college/")
def epass(request, application_id):
	application = get_object_or_404(
		PassApplication,
		id=application_id,
		applicant=request.user,
		status="PAYMENT_COMPLETED"
	)
	pass_obj = get_object_or_404(EPass, application=application)
	ensure_epass_qr(pass_obj)

	return render(
		request,
		"users/epass.html",
		{
			"application": application,
			"pass_obj": pass_obj,
		}
	)


def _safe_pass_field(application, *field_names, default="-"):
	for field_name in field_names:
		value = getattr(application, field_name, None)
		if value not in (None, ""):
			return value
	return default


def _is_valid_epass_application(application, request):
	if application.applicant_id == getattr(request.user, "id", None):
		return True
	if (
		application.applicant_id is None
		and request.user.is_authenticated
		and getattr(request.user, "is_staff", False)
	):
		return True
	if (
		application.pass_type == "SCHOOL"
		and request.session.get("school_payment_application_id") == application.id
	):
		return True
	return False


def _get_epass_application_for_request(request, application_id):
	application = get_object_or_404(
		PassApplication.objects.filter(status__in=[
			"PAYMENT_COMPLETED",
			"APPROVED",
			"COLLEGE_APPROVED",
			"SCHOOL_APPROVED",
		]),
		id=application_id,
	)
	if not _is_valid_epass_application(application, request):
		raise Http404
	return application


def _file_to_data_url(file_field):
	if not file_field:
		return ""
	name = getattr(file_field, "name", "") or ""
	if not name:
		return ""
	storage = getattr(file_field, "storage", None)
	if storage is None:
		return ""
	try:
		if not storage.exists(name):
			return ""
		with storage.open(name, "rb") as file_obj:
			file_bytes = file_obj.read()
	except Exception:
		return ""
	content_type = guess_type(name)[0] or "application/octet-stream"
	encoded = base64.b64encode(file_bytes).decode("ascii")
	return f"data:{content_type};base64,{encoded}"


def _build_epass_pdf(application, pass_obj):
	buffer = BytesIO()
	pdf = canvas.Canvas(buffer, pagesize=A4)
	width, height = A4

	card_x = 25
	card_y = 30
	card_w = 540
	card_h = 790

	pdf.setFillColor(colors.HexColor("#EEF5FB"))
	pdf.rect(card_x, card_y, card_w, card_h, fill=1, stroke=0)
	pdf.setStrokeColor(colors.HexColor("#D8E5F2"))
	pdf.setLineWidth(1.5)
	pdf.roundRect(card_x, card_y, card_w, card_h, 16, fill=0, stroke=1)

	# Header band
	header_y = card_y + card_h - 100
	pdf.setFillColor(colors.HexColor("#EAF3FA"))
	pdf.roundRect(card_x + 12, card_y + card_h - 92, card_w - 24, 78, 16, fill=1, stroke=0)

	# Left brand block
	pdf.setFillColor(colors.HexColor("#0B3F74"))
	pdf.setFont("Helvetica-Bold", 38)
	pdf.drawString(card_x + 26, header_y + 30, "YOVAA")
	pdf.setFont("Helvetica", 12)
	pdf.drawString(card_x + 31, header_y + 10, "Your Journey")
	pdf.drawString(card_x + 180, header_y + 10, "Your Support")

	# Center title block
	pdf.setFillColor(colors.HexColor("#1E4A79"))
	pdf.setFont("Helvetica-Bold", 18)
	pdf.drawCentredString(card_x + 350, header_y + 40, "UNIFIED BUS PASS SYSTEM")
	pdf.drawCentredString(card_x + 350, header_y + 18, "STUDENT E-PASS")

	# Right side bus icon and tagline
	pdf.setFillColor(colors.HexColor("#0B5B8C"))
	pdf.setFont("Helvetica", 30)
	pdf.drawString(card_x + 495, header_y + 20, "🚌")
	pdf.setFont("Helvetica-Oblique", 13)
	pdf.setFillColor(colors.HexColor("#0C4D88"))
	pdf.drawRightString(card_x + 520, header_y + 3, "Safe Ride Bright Future")

	# Main content area
	content_left_x = card_x + 34
	content_top_y = card_y + 620
	content_box_x = card_x + 32
	content_box_y = card_y + 210
	content_box_w = 320
	content_box_h = 205
	pdf.setStrokeColor(colors.HexColor("#0B5B8C"))
	pdf.setFillColor(colors.HexColor("#DDEAF7"))
	pdf.roundRect(content_box_x, content_box_y, content_box_w, content_box_h, 12, fill=1, stroke=1)

	# Detail list
	pdf.setFillColor(colors.HexColor("#0F3764"))
	pdf.setFont("Helvetica-Bold", 13)
	rows = [
		("Name", application.full_name),
		(
			"UMIS Number",
			_safe_pass_field(application, "verification_id", "registration_number", default="-"),
		),
		("Reg Number", _safe_pass_field(application, "registration_number", default="-")),
		("College Name", _safe_pass_field(application, "college_name", default="-")),
		("Department", _safe_pass_field(application, "department", default="-")),
		(
			"Academic Year",
			_safe_pass_field(application, "academic_year", default="2024 - 2025"),
		),
		(
			"Current Year",
			_safe_pass_field(application, "current_year", default="2nd Year"),
		),
	]
	for idx, (label, value) in enumerate(rows):
		y = content_top_y - idx * 28
		pdf.drawString(content_left_x, y, label)
		pdf.drawString(content_left_x + 170, y, ":")
		pdf.setFont("Helvetica-Bold", 12)
		pdf.drawString(content_left_x + 190, y, str(value))
		pdf.setFont("Helvetica-Bold", 13)

	# Photo and QR right side
	photo_x = card_x + 360
	photo_y = card_y + 315
	photo_w = 170
	photo_h = 160
	pdf.setStrokeColor(colors.HexColor("#0B5B8C"))
	pdf.setFillColor(colors.HexColor("#DDEAF7"))
	pdf.roundRect(photo_x, photo_y, photo_w, photo_h, 12, fill=1, stroke=1)
	if application.applicant_photo and application.applicant_photo.storage.exists(application.applicant_photo.name):
		try:
			if hasattr(application.applicant_photo, "open"):
				application.applicant_photo.open("rb")
			photo = application.applicant_photo.file
			pdf.drawInlineImage(photo, photo_x + 8, photo_y + 8, width=154, height=144)
		except Exception:
			pass
	else:
		pdf.setFillColor(colors.HexColor("#A9BDD2"))
		pdf.setFont("Helvetica-Bold", 12)
		pdf.drawCentredString(photo_x + photo_w / 2, photo_y + photo_h / 2, "PHOTO")

	qr_x = card_x + 360
	qr_y = card_y + 110
	qr_w = 170
	qr_h = 120
	pdf.roundRect(qr_x, qr_y, qr_w, qr_h, 12, fill=1, stroke=1)
	if pass_obj.qr_code and pass_obj.qr_code.storage.exists(pass_obj.qr_code.name):
		try:
			qr = pass_obj.qr_code.file
			pdf.drawInlineImage(qr, qr_x + 12, qr_y + 10, width=146, height=100)
		except Exception:
			pass
	pdf.setFont("Helvetica-Bold", 12)
	pdf.setFillColor(colors.HexColor("#0D4D88"))
	pdf.drawCentredString(qr_x + 85, qr_y - 10, "Scan to Verify")

	# Pass info chips
	chip_y = card_y + 160
	chip_left_w = 220
	chip_right_w = 130
	chip_left_x = card_x + 320
	chip_right_x = card_x + 545
	pdf.setFillColor(colors.HexColor("#CFEAF8"))
	pdf.roundRect(chip_left_x, chip_y, chip_left_w, 55, 12, fill=1, stroke=0)
	pdf.roundRect(chip_right_x, chip_y, chip_right_w, 55, 12, fill=1, stroke=0)
	pdf.setFillColor(colors.HexColor("#0E457D"))
	pdf.setFont("Helvetica-Bold", 10)
	pdf.drawString(chip_left_x + 16, chip_y + 33, "Pass Type")
	pdf.setFont("Helvetica-Bold", 18)
	pdf.drawString(chip_left_x + 16, chip_y + 10, str(application.get_pass_type_display() or "College Student"))
	pdf.setFont("Helvetica-Bold", 10)
	pdf.drawString(chip_right_x + 16, chip_y + 33, "Valid")
	pdf.setFont("Helvetica-Bold", 18)
	pdf.drawString(chip_right_x + 16, chip_y + 10, str(pass_obj.valid_until or pass_obj.expiry_date).split('-')[-1] if pass_obj.valid_until or pass_obj.expiry_date else "-")

	# Footer strip
	footer_y = card_y + 10
	pdf.setFillColor(colors.HexColor("#0B5B8C"))
	pdf.rect(card_x, footer_y, card_w, 80, fill=1, stroke=0)
	pdf.setFillColor(colors.white)
	pdf.setFont("Helvetica-Bold", 30)
	pdf.drawString(card_x + 16, footer_y + 32, "YOVAA")
	pdf.setFont("Helvetica-Bold", 18)
	pdf.drawString(card_x + 16, footer_y + 12, "Bus Pass")
	pdf.drawString(card_x + 206, footer_y + 32, "|")
	pdf.setFont("Helvetica-Bold", 24)
	pdf.drawString(card_x + 230, footer_y + 32, "Travel Smart")
	pdf.drawString(card_x + 230, footer_y + 12, "Save Time")
	pdf.setFillColor(colors.HexColor("#D9EDFF"))
	pdf.roundRect(card_x + 450, footer_y + 12, 90, 54, 18, fill=1, stroke=0)
	pdf.setStrokeColor(colors.white)
	pdf.setLineWidth(2)
	pdf.line(card_x + 468, footer_y + 30, card_x + 518, footer_y + 52)
	pdf.line(card_x + 480, footer_y + 30, card_x + 530, footer_y + 52)
	pdf.circle(card_x + 490, footer_y + 40, 14, fill=0, stroke=1)

	pdf.save()
	return buffer.getvalue()


@login_required(login_url="/accounts/login/general/")
def e_pass_download(request, e_pass_id):
	pass_obj = get_object_or_404(
		EPass.objects.select_related("application"),
		id=e_pass_id,
		application__status__in=[
			"PAYMENT_COMPLETED",
			"APPROVED",
			"COLLEGE_APPROVED",
			"SCHOOL_APPROVED",
		],
	)
	application = pass_obj.application
	is_owner = application.applicant_id == request.user.id
	is_staff_pass = (
		application.applicant_id is None
		and request.user.is_authenticated
		and getattr(request.user, "is_staff", False)
	)
	is_school_session_match = (
		application.pass_type == "SCHOOL"
		and request.session.get("school_payment_application_id") == application.id
	)
	if not (is_owner or is_staff_pass or is_school_session_match):
		raise Http404
	ensure_epass_qr(pass_obj)
	pdf_bytes = _build_epass_pdf(application, pass_obj)
	response = HttpResponse(pdf_bytes, content_type="application/pdf")
	response["Content-Disposition"] = f'attachment; filename="{application.application_number}.pdf"'
	return response


@login_required(login_url="/accounts/login/general/")
def epass_download(request, application_id):
	application = _get_epass_application_for_request(request, application_id)
	pass_obj = get_object_or_404(EPass, application=application)
	ensure_epass_qr(pass_obj)
	pdf_bytes = _build_epass_pdf(application, pass_obj)
	response = HttpResponse(pdf_bytes, content_type="application/pdf")
	response["Content-Disposition"] = f'attachment; filename="{application.application_number}.pdf"'
	return response


@login_required(login_url="/accounts/login/general/")
def epass_html_download(request, application_id):
	application = _get_epass_application_for_request(request, application_id)
	pass_obj = get_object_or_404(EPass, application=application)
	ensure_epass_qr(pass_obj)
	response = render(
		request,
		"users/epass_html_export.html",
		{
			"application": application,
			"pass_obj": pass_obj,
			"photo_data_url": _file_to_data_url(application.applicant_photo),
			"qr_data_url": _file_to_data_url(pass_obj.qr_code),
		},
	)
	response["Content-Disposition"] = f'attachment; filename="{application.application_number}.html"'
	response["Content-Type"] = "text/html; charset=utf-8"
	return response


@login_required(login_url="/accounts/login/general/")
def e_pass(request, e_pass_id):
	pass_obj = get_object_or_404(
		EPass.objects.select_related("application"),
		id=e_pass_id,
		application__status__in=[
			"PAYMENT_COMPLETED",
			"APPROVED",
			"COLLEGE_APPROVED",
			"SCHOOL_APPROVED",
		],
	)
	application = pass_obj.application
	is_owner = application.applicant_id == request.user.id
	is_staff_pass = (
		application.applicant_id is None
		and request.user.is_authenticated
		and getattr(request.user, "is_staff", False)
	)
	is_school_session_match = (
		application.pass_type == "SCHOOL"
		and request.session.get("school_payment_application_id") == application.id
	)
	if not (is_owner or is_staff_pass or is_school_session_match):
		raise Http404
	ensure_epass_qr(pass_obj)
	return render(
		request,
		"users/epass.html",
		{"application": application, "pass_obj": pass_obj}
	)


def verify_qr(request):
	qr_data = request.GET.get("data", "")
	if not qr_data:
		return render(
			request,
			"users/qr_result.html",
			{"status": "INVALID", "pass_obj": None}
		)

	# Accept legacy PASS:<number>|... payloads as well as new raw numbers.
	pass_number = qr_data.split("|", 1)[0].removeprefix("PASS:")
	pass_obj = EPass.objects.filter(pass_number=pass_number).first()
	if pass_obj is None:
		return render(
			request,
			"users/qr_result.html",
			{"status": "INVALID", "pass_obj": None}
		)

	today = date.today()
	if not pass_obj.is_active:
		status = "INVALID"
	elif today > pass_obj.expiry_date:
		status = "EXPIRED"
	else:
		status = "VALID"

	return render(
		request,
		"users/qr_result.html",
		{"pass_obj": pass_obj, "status": status}
	)


def verify_pass(request):
	result = None

	if request.method == "POST":
		pass_number = request.POST.get("pass_number", "").strip()
		pass_obj = EPass.objects.select_related("application").filter(
			pass_number=pass_number
		).first()

		if pass_obj is None:
			result = {
				"status": "INVALID",
				"message": "Pass not found."
			}
		else:
			valid_until = pass_obj.valid_until or pass_obj.expiry_date
			if date.today() > valid_until:
				result = {
					"status": "EXPIRED",
					"message": "This bus pass has expired.",
					"pass_obj": pass_obj
				}
			elif (
				pass_obj.application.status != "PAYMENT_COMPLETED"
				or not pass_obj.is_active
			):
				result = {
					"status": "INVALID",
					"message": "This bus pass is not active.",
					"pass_obj": pass_obj
				}
			else:
				result = {
					"status": "VALID",
					"message": "Bus pass is valid.",
					"pass_obj": pass_obj
				}

	return render(request, "users/verify_pass.html", {"result": result})


def qr_scanner(request):
	return render(request, "users/qr_scanner.html")
