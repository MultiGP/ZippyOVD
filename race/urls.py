from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("race/admin/", views.race_admin, name="race_admin"),
    path("race/bug/", views.race_bug, name="race_bug"),
    path("race/api/config/", views.api_config, name="api_config"),
    path("race/api/action/", views.api_action, name="api_action"),
    path("race/api/telemetry/", views.api_telemetry, name="api_telemetry"),
    path("race/api/state/", views.api_state, name="api_state"),
    path("race/api/stream/", views.api_stream, name="api_stream"),
    path("race/api/logos/", views.api_logos, name="api_logos"),
    path("race/api/logos/upload/", views.api_logo_upload, name="api_logo_upload"),
    path("race/api/logos/assign/", views.api_logo_assign, name="api_logo_assign"),
    path("race/api/logos/<str:logo_id>/", views.api_logo_delete, name="api_logo_delete"),
    path("race/api/logos/file/<str:logo_id>/", views.api_logo_file, name="api_logo_file"),
]
