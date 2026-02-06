#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


MIN_PYTHON = (3, 10)


def ensure_python_version() -> None:
    if sys.version_info < MIN_PYTHON:
        current = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        required = ".".join(str(n) for n in MIN_PYTHON)
        raise SystemExit(
            f"Python {required}+ is required. Current interpreter: {current}"
        )


def main() -> None:
    """Run administrative tasks."""
    ensure_python_version()
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skills_runtime_service.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
