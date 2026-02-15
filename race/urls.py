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
]
