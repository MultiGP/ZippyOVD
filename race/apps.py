import os
import sys

from django.apps import AppConfig


class RaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "race"

    def ready(self) -> None:
        # Django runserver with autoreload starts a parent + child process.
        # Only skip parent when autoreload is enabled.
        if "runserver" in sys.argv:
            run_main = os.environ.get("RUN_MAIN")
            no_reload = "--noreload" in sys.argv
            if run_main != "true" and not no_reload:
                return

        from .state import get_machine_ip
        from .velocidrone import client

        machine_ip = get_machine_ip()
        if machine_ip:
            client.configure(machine_ip)
