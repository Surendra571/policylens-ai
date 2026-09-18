#!/usr/bin/env python
import os
import sys
from pathlib import Path

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    base_dir = Path(__file__).resolve().parent
    sys.path.insert(0, str(base_dir))
    sys.path.insert(0, str(base_dir / "apps"))
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django.") from exc
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
