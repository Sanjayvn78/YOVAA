from django.urls import path

from .views import (
    college_dashboard,
    college_tracking,
    dashboard,
    disabled_dashboard,
    general_dashboard,
    login_college,
    login_disabled,
    login_general,
    login_special,
    login_view,
    logout_view,
    register_college,
    register_disabled,
    register_general,
    register_special,
    register_view,
    special_dashboard,
    special_generate_pass,
)


urlpatterns = [
    path("register/<str:user_type>/", register_view, name="register"),
    path("login/<str:user_type>/", login_view, name="login"),
    path("dashboard/", dashboard, name="account_dashboard"),
    path("logout/", logout_view, name="account_logout"),
    path("college/register/", register_college, name="college_register"),
    path("college/login/", login_college, name="college_login"),
    path("college/dashboard/", college_dashboard, name="college_dashboard"),
    path("college/tracking/", college_tracking, name="college_tracking"),
    path(
        "college/tracking/<int:application_id>/",
        college_tracking,
        name="college_application_tracking",
    ),
    path("disabled/register/", register_disabled, name="disabled_register"),
    path("disabled/login/", login_disabled, name="disabled_login"),
    path("disabled/dashboard/", disabled_dashboard, name="disabled_dashboard"),
    path("general/register/", register_general, name="general_register"),
    path("general/login/", login_general, name="general_login"),
    path("general/dashboard/", general_dashboard, name="general_dashboard"),
    path("special/register/", register_special, name="special_register"),
    path("special/login/", login_special, name="special_login"),
    path("special/dashboard/", special_dashboard, name="special_dashboard"),
    path("special/generate-pass/", special_generate_pass, name="special_generate_pass"),
]