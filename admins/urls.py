from django.urls import path
from .views import (
    admins_home,
    school_admin,
    school_epass,
    school_apply,
    school_application,
    school_application_review,
    school_verify_application,
    college_admin,
    college_admin_dashboard,
    college_application_review,
    college_verify_application,
    transport_admin,
    transport_school_portal,
    transport_general_portal,
    transport_college_portal,
    transport_college_application_detail,
    transport_disabled_portal,
    transport_special_portal,
    transport_verify_special_application,
    transport_send_college,
    transport_allow_payment,
    transport_verify_general_payment,
    transport_verify_payment,
    admin_login,
    admin_logout,
)


urlpatterns = [
    path("", admins_home, name="admins_home"),
    path("college/login/", lambda request: admin_login(request, "college"), name="college_admin_login"),
    path("school/login/", lambda request: admin_login(request, "school"), name="school_admin_login"),
    path("logout/", admin_logout, name="admin_logout"),
    path("school/", school_admin, name="school_admin"),
    path(
        "school/application/<int:application_id>/epass/",
        school_epass,
        name="school_epass",
    ),
    path("school/apply/", school_apply, name="school_apply"),
    path(
        "school/application/",
        school_application,
        name="school_application"
    ),
    path(
        "school/application/<int:application_id>/review/",
        school_application_review,
        name="school_application_review"
    ),
    path(
        "school/application/<int:application_id>/verify/",
        school_verify_application,
        name="school_verify_application"
    ),
    path("college/", college_admin, name="college_admin"),
    path(
        "college/dashboard/",
        college_admin_dashboard,
        name="college_admin_dashboard"
    ),
    path(
        "college/application/<int:application_id>/",
        college_application_review,
        name="college_application_review"
    ),
    path(
        "college/application/<int:application_id>/verify/",
        college_verify_application,
        name="college_verify_application"
    ),
    path("transport/", transport_admin, name="transport_admin"),
    path(
        "transport/school/",
        transport_school_portal,
        name="transport_school_portal"
    ),
    path(
        "transport/general/",
        transport_general_portal,
        name="transport_general_portal"
    ),
    path(
        "transport/college/",
        transport_college_portal,
        name="transport_college_portal"
    ),
    path(
        "transport/college/application/<int:application_id>/",
        transport_college_application_detail,
        name="transport_college_application_detail"
    ),
    path(
        "transport/disabled/",
        transport_disabled_portal,
        name="transport_disabled_portal"
    ),
    path(
        "transport/special/",
        transport_special_portal,
        name="transport_special_portal"
    ),
    path(
        "transport/special/<int:application_id>/verify/",
        transport_verify_special_application,
        name="transport_verify_special_application"
    ),
    path(
        "transport/college/<int:application_id>/send/",
        transport_send_college,
        name="transport_send_college"
    ),
    path(
        "transport/college/<int:application_id>/allow-payment/",
        transport_allow_payment,
        name="transport_allow_payment"
    ),
    path(
        "transport/general/<int:application_id>/verify-payment/",
        transport_verify_general_payment,
        name="transport_verify_general_payment"
    ),
    path(
        "transport/payment/<int:application_id>/verify/",
        transport_verify_payment,
        name="transport_verify_payment"
    ),
    path("college/login/", lambda request: admin_login(request, "college"), name="college_admin_login"),
    path("school/login/", lambda request: admin_login(request, "school"), name="school_admin_login"),
    path("logout/", admin_logout, name="admin_logout"),
]