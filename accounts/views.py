from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from passes.models import PassApplication

from verification.models import (
    DisabledPerson,
    GovernmentTransportStaff,
    UMISStudent,
)

from .models import UserProfile


USER_TYPES = {
    "college": "COLLEGE",
    "disabled": "DISABLED",
    "general": "GENERAL",
    "special": "SPECIAL",
}

SPECIAL_STAFF_STATUSES = {"ACTIVE", "PERMANENT"}


def _user_type(value):
    return USER_TYPES.get(value.lower())


def _dashboard_route(normalized_type):
    return {
        "COLLEGE": "college_dashboard",
        "DISABLED": "disabled_dashboard",
        "GENERAL": "general_dashboard",
        "SPECIAL": "special_dashboard",
    }[normalized_type]


def _permanent_special_staff(staff_number):
    staff = GovernmentTransportStaff.objects.filter(
        staff_number__iexact=staff_number,
        is_eligible=True,
        is_active=True,
    ).first()
    if staff is None:
        return None
    if staff.employment_status.strip().upper() not in SPECIAL_STAFF_STATUSES:
        return None
    return staff


def _special_login_view(request):
    error = None
    if request.method == "POST":
        staff = _permanent_special_staff(
            request.POST.get("identifier", "").strip()
        )
        if staff is None:
            error = "Only active permanent staff can use the special pass."
        else:
            request.session["special_staff_id"] = staff.id
            return redirect("special_dashboard")

    return render(request, "accounts/special_login.html", {"error": error})


def register_view(request, user_type):
    normalized_type = _user_type(user_type)
    if normalized_type is None:
        return redirect("home")
    if normalized_type == "SPECIAL":
        return redirect("special_login")

    error = None
    next_url = request.POST.get("next", "") or request.GET.get("next", "")
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        phone_number = request.POST.get("phone_number", "").strip()
        login_identifier = phone_number.lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        identifier = request.POST.get("identifier", "").strip()
        email = request.POST.get("email", "").strip().lower()

        if password != confirm_password:
            error = "Passwords do not match."
        elif not name or not password:
            error = "All required fields must be completed."
        elif normalized_type == "COLLEGE" and not email:
            error = "College email is required."
        elif normalized_type != "COLLEGE" and not phone_number:
            error = "Phone number is required."
        elif normalized_type != "COLLEGE" and len(phone_number) > 15:
            error = "Phone number must be 15 characters or fewer."
        elif normalized_type == "COLLEGE":
            student = UMISStudent.objects.filter(
                Q(registration_number__iexact=identifier)
                | Q(umis_number__iexact=identifier),
                name__iexact=name,
                is_active=True
            ).first()
            if student is None:
                error = "Registration number and name do not match UMIS."
        elif normalized_type == "DISABLED":
            person = DisabledPerson.objects.filter(
                disability_id__iexact=identifier,
                name__iexact=name,
                is_active=True
            ).first()
            if person is None:
                error = "Disability ID and name do not match the dataset."
        elif normalized_type == "SPECIAL":
            staff = GovernmentTransportStaff.objects.filter(
                staff_number__iexact=identifier,
                name__iexact=name,
                employment_status__iexact="ACTIVE",
                is_eligible=True,
                is_active=True
            ).first()
            if staff is None:
                error = "Staff number, name, or eligibility is invalid."

        username = email if normalized_type == "COLLEGE" else login_identifier
        if error is None and User.objects.filter(username=username).exists():
            error = "An account already exists for these login details."

        if error is None:
            user = User.objects.create_user(
                username=username,
                email=email if normalized_type == "COLLEGE" else "",
                password=password,
                first_name=name,
            )
            profile = UserProfile.objects.create(
                user=user,
                user_type=normalized_type,
                phone_number=login_identifier,
                registration_number=(identifier if normalized_type == "COLLEGE" else ""),
                disability_id=(identifier if normalized_type == "DISABLED" else ""),
                staff_number=(identifier if normalized_type == "SPECIAL" else ""),
            )
            login(request, user)
            if next_url.startswith("/"):
                return redirect(next_url)
            return redirect(_dashboard_route(normalized_type))

    return render(request, f"accounts/{user_type.lower()}_register.html", {
        "user_type": normalized_type,
        "error": error,
        "next": next_url,
    })


def login_view(request, user_type):
    normalized_type = _user_type(user_type)
    if normalized_type is None:
        return redirect("home")
    if normalized_type == "SPECIAL":
        return _special_login_view(request)

    error = None
    next_url = request.GET.get("next", "")
    if request.method == "POST":
        next_url = request.POST.get("next", "") or next_url
        identifier = request.POST.get("identifier", "").strip().lower()
        password = request.POST.get("password", "")
        username = identifier
        if normalized_type == "COLLEGE":
            matched_user = User.objects.filter(
                email__iexact=identifier
            ).first()
        else:
            matched_profile = UserProfile.objects.filter(
                Q(phone_number__iexact=identifier)
                | Q(user__username__iexact=identifier)
                | Q(user__email__iexact=identifier),
                user__is_active=True
            ).select_related("user").first()
            matched_user = matched_profile.user if matched_profile else None

        if matched_user is not None:
            username = matched_user.username
        user = authenticate(request, username=username, password=password)
        profile = getattr(user, "profile", None) if user else None
        if profile is None or profile.user_type != normalized_type:
            if normalized_type == "COLLEGE" and matched_user is None:
                error = "College account not found. Register first with your UMIS details."
            elif normalized_type == "COLLEGE":
                error = "Invalid college email or password."
            else:
                error = "Invalid login details for this user type."
        else:
            login(request, user)
            if next_url.startswith("/"):
                return redirect(next_url)
            return redirect(_dashboard_route(normalized_type))

    return render(request, f"accounts/{user_type.lower()}_login.html", {
        "user_type": normalized_type,
        "error": error,
        "next": next_url,
    })


@login_required(login_url="/accounts/login/general/")
def dashboard(request):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"user_type": "GENERAL"},
    )
    return redirect(_dashboard_route(profile.user_type))


def _typed_dashboard(request, expected_type, applications=None):
    profile, _ = UserProfile.objects.get_or_create(
        user=request.user,
        defaults={"user_type": expected_type},
    )
    if profile.user_type != expected_type:
        return redirect(_dashboard_route(profile.user_type))
    dataset = None
    if expected_type == "COLLEGE":
        dataset = UMISStudent.objects.filter(
            Q(registration_number__iexact=profile.registration_number)
            | Q(umis_number__iexact=profile.registration_number)
        ).filter(name__iexact=request.user.first_name).first()
    elif expected_type == "DISABLED":
        dataset = DisabledPerson.objects.filter(
            disability_id=profile.disability_id
        ).first()
    elif expected_type == "SPECIAL":
        dataset = GovernmentTransportStaff.objects.filter(
            staff_number=profile.staff_number
        ).first()

    template_name = (
        "accounts/general_dashboard.html"
        if expected_type == "GENERAL"
        else "accounts/student_dashboard.html"
    )
    return render(request, template_name, {
        "profile": profile,
        "dataset": dataset,
        "dashboard_type": expected_type,
        "applications": applications,
        "total": applications.count() if applications is not None else 0,
        "pending_count": applications.filter(
            status__in=[
                "TRANSPORT_VERIFICATION",
                "COLLEGE_VERIFICATION",
                "PAYMENT_PENDING",
                "SUBMITTED",
            ]
        ).count() if applications is not None else 0,
        "approved_count": applications.filter(
            status__in=[
                "COLLEGE_APPROVED",
                "PAYMENT_PENDING",
                "PAYMENT_COMPLETED",
            ]
        ).count() if applications is not None else 0,
        "epass_count": applications.filter(
            status="PAYMENT_COMPLETED",
            epass__isnull=False,
        ).count() if applications is not None else 0,
        "today": timezone.localdate(),
    })


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required(login_url="/accounts/login/college/")
def college_dashboard(request):
    applications = PassApplication.objects.filter(
        applicant=request.user,
        pass_type="COLLEGE",
    ).order_by("-created_at")
    return _typed_dashboard(
        request,
        "COLLEGE",
        applications=applications,
    )


@login_required(login_url="/accounts/login/college/")
def college_tracking(request, application_id=None):
    profile = getattr(request.user, "profile", None)
    if profile is None or profile.user_type != "COLLEGE":
        return redirect("account_dashboard")

    applications = PassApplication.objects.filter(
        applicant=request.user,
        pass_type="COLLEGE",
    ).order_by("-created_at")
    selected_application = None
    if application_id is not None:
        selected_application = get_object_or_404(
            applications,
            id=application_id,
        )
    return render(
        request,
        "accounts/college_tracking.html",
        {
            "applications": applications,
            "selected_application": selected_application,
            "today": timezone.localdate(),
        },
    )


@login_required(login_url="/accounts/login/disabled/")
def disabled_dashboard(request):
    applications = PassApplication.objects.filter(
        applicant=request.user,
        pass_type="DISABLED",
    ).order_by("-created_at")
    return _typed_dashboard(request, "DISABLED", applications=applications)


@login_required(login_url="/accounts/login/general/")
def general_dashboard(request):
    applications = PassApplication.objects.filter(
        applicant=request.user,
        pass_type="GENERAL",
    ).order_by("-created_at")
    return _typed_dashboard(request, "GENERAL", applications=applications)


def special_dashboard(request):
    staff_id = request.session.get("special_staff_id")
    staff = GovernmentTransportStaff.objects.filter(
        id=staff_id,
        is_eligible=True,
        is_active=True,
    ).first()
    if staff is None or staff.employment_status.strip().upper() not in SPECIAL_STAFF_STATUSES:
        request.session.pop("special_staff_id", None)
        return redirect("special_login")
    return render(request, "accounts/special_dashboard.html", {"staff": staff})


def special_generate_pass(request):
    staff_id = request.session.get("special_staff_id")
    staff = GovernmentTransportStaff.objects.filter(
        id=staff_id,
        is_eligible=True,
        is_active=True,
    ).first()
    if staff is None or staff.employment_status.strip().upper() not in SPECIAL_STAFF_STATUSES:
        request.session.pop("special_staff_id", None)
        return redirect("special_login")

    application = PassApplication.objects.filter(
        pass_type="SPECIAL",
        staff_number=staff.staff_number,
    ).order_by("-created_at").first()

    if request.method == "POST":
        required_documents = {
            "applicant_photo": request.FILES.get("applicant_photo"),
            "address_proof_document": request.FILES.get("address_proof_document"),
            "signature_document": request.FILES.get("signature_document"),
            "staff_id_card_document": request.FILES.get("staff_id_card_document"),
        }
        missing_documents = [
            label for field, label in [
                ("applicant_photo", "photo"),
                ("address_proof_document", "address proof"),
                ("signature_document", "signature"),
                ("staff_id_card_document", "staff ID card"),
            ] if not required_documents[field]
        ]
        if missing_documents:
            return render(
                request,
                "accounts/special_documents.html",
                {"staff": staff, "application": application, "missing_documents": missing_documents},
            )

        if application is None:
            application = PassApplication.objects.create(
                application_number=(
                    f"SPC-{staff.staff_number}-"
                    f"{timezone.now().strftime('%Y%m%d%H%M%S')}"
                ),
                pass_type="SPECIAL",
                application_type="NEW",
                status="APPROVED",
                verification_id=staff.staff_number,
                full_name=staff.name,
                staff_number=staff.staff_number,
                department=staff.designation,
                date_of_birth=staff.date_of_birth,
                address=staff.workplace,
                district=staff.district,
            )
        else:
            application.status = "APPROVED"

        application.department = staff.designation
        for field, document in required_documents.items():
            setattr(application, field, document)
        application.save()

        if not hasattr(application, "epass"):
            from users.views import generate_epass

            generate_epass(application)

        from users.views import ensure_epass_qr

        pass_obj = application.epass
        ensure_epass_qr(pass_obj)
        return render(
            request,
            "users/epass.html",
            {"application": application, "pass_obj": pass_obj},
        )

    return render(
        request,
        "accounts/special_documents.html",
        {"staff": staff, "application": application},
    )


def register_college(request):
    return register_view(request, "college")


def register_disabled(request):
    return register_view(request, "disabled")


def register_general(request):
    return register_view(request, "general")


def register_special(request):
    return register_view(request, "special")


def login_college(request):
    return login_view(request, "college")


def login_disabled(request):
    return login_view(request, "disabled")


def login_general(request):
    return login_view(request, "general")


def login_special(request):
    return login_view(request, "special")
