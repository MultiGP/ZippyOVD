#!/usr/bin/env python3
import os
import sys


def main() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "zippyovd.settings")
    from django.core.management import execute_from_command_line

    # Default runserver binding for LAN access
    if len(sys.argv) >= 2 and sys.argv[1] == "runserver":
        has_addrport = any(
            not arg.startswith("-")
            for arg in sys.argv[2:]
        )
        if not has_addrport:
            sys.argv.append("0.0.0.0:8000")

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
