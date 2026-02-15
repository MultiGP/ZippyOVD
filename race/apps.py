import os
import sys

from django.apps import AppConfig


class RaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "race"

    def ready(self) -> None:
        # Django runserver with autoreload starts a parent + child process.
        # Only start the Velocidrone client in the serving child process.
        if "runserver" in sys.argv and os.environ.get("RUN_MAIN") != "true":
            return

        from .state import get_machine_ip
        from .velocidrone import client

        machine_ip = get_machine_ip()
        if machine_ip:
            client.configure(machine_ip)
