from django.apps import AppConfig


class RaceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "race"

    def ready(self) -> None:
        from .state import get_machine_ip
        from .velocidrone import client

        machine_ip = get_machine_ip()
        if machine_ip:
            client.configure(machine_ip)
