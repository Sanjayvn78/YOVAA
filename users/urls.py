from django.urls import path
from .views import (
    users_home,
    college_pass,
    college_application,
    disabled_pass,
    create_disabled_application,
    disabled_application,
    general_pass,
    special_pass,
    create_special_application,
    special_application,
    payment,
    payment_success,
    epass,
    epass_download,
    epass_html_download,
    e_pass_download,
    user_dashboard,
    admin_dashboard,
    conductor_dashboard,
    school_admin,
    create_school_pass,
    college_admin,
    create_college_pass,
    user_application_detail,
    renew_pass,
    verify_qr,
    qr_scanner,
    e_pass,
    verify_pass,
    college_apply,
    college_details,
    disabled_apply,
    disabled_details,
    special_apply,
    special_details,
    general_apply,
    general_travel,
    payment_verify,
)


urlpatterns = [
    path("", users_home, name="users_home"),
    path("college-pass/", college_pass, name="college_pass"),
    path(
        "college-application/",
        college_application,
        name="college_application"
    ),
    path("disabled-pass/", disabled_pass, name="disabled_pass"),
    path(
        "disabled-application/",
        disabled_application,
        name="disabled_application"
    ),
    path("general-pass/", general_pass, name="general_pass_legacy"),
    path("special-pass/", special_pass, name="special_pass"),
    path(
        "special-application/",
        special_application,
        name="special_application"
    ),
    path("payment/<int:application_id>/", payment, name="payment"),
    path(
        "payment/<int:application_id>/verify/",
        payment_verify,
        name="payment_verify"
    ),
    path(
        "payment/<int:application_id>/success/",
        payment_success,
        name="payment_success"
    ),
    path("epass/<int:application_id>/", epass, name="epass"),
    path("epass/<int:application_id>/download/", epass_download, name="epass_download"),
    path("epass/<int:application_id>/download-html/", epass_html_download, name="epass_html_download"),
    path("e-pass/<int:e_pass_id>/", e_pass, name="e_pass"),
    path("e-pass/<int:e_pass_id>/download/", e_pass_download, name="e_pass_download_alt"),
    path("verify-pass/", verify_pass, name="verify_pass"),
    path("dashboard/", user_dashboard, name="user_dashboard"),
    path("admin/", admin_dashboard, name="admin_dashboard"),
    path("conductor/", conductor_dashboard, name="conductor_dashboard"),
    path("admin/school/", school_admin, name="school_admin"),
    path("admin/college/", college_admin, name="college_admin"),
    path(
        "admin/college/create-pass/<int:student_id>/",
        create_college_pass,
        name="create_college_pass"
    ),
    path(
        "admin/school/create-pass/<int:student_id>/",
        create_school_pass,
        name="create_school_pass"
    ),
    path(
        "application/<int:application_id>/",
        user_application_detail,
        name="user_application_detail"
    ),
    path("renew/<int:application_id>/", renew_pass, name="renew_pass"),
    path("verify-qr/", verify_qr, name="verify_qr"),
    path("qr-scanner/", qr_scanner, name="qr_scanner"),
    path("apply/college/", college_apply, name="college_apply"),
    path(
        "apply/college/details/",
        college_details,
        name="college_details"
    ),
    path("apply/disabled/", disabled_pass, name="disabled_apply"),
    path(
        "apply/disabled/create/<int:person_id>/",
        create_disabled_application,
        name="create_disabled_application"
    ),
    path(
        "apply/disabled/details/",
        disabled_details,
        name="disabled_details"
    ),
    path("apply/special/", special_apply, name="special_apply"),
    path(
        "apply/special/create/<int:staff_id>/",
        create_special_application,
        name="create_special_application"
    ),
    path(
        "apply/special/details/",
        special_details,
        name="special_details"
    ),
    path("apply/general/", general_pass, name="general_pass"),
    path(
        "apply/general/travel/",
        general_travel,
        name="general_travel"
    ),
]