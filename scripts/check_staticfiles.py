#!/usr/bin/env python
"""Fail deployment when critical public static assets are missing."""

from pathlib import Path
import os
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")

try:
    import django
    from django.conf import settings
except Exception as exc:
    print(f"Unable to load Django settings: {exc}", file=sys.stderr)
    raise SystemExit(1)

django.setup()

static_root = Path(settings.STATIC_ROOT)
required_assets = [
    "css/eshelle.css",
    "css/eshelle-premium.css",
    "css/home.css",
    "css/langues.css",
    "css/lesson_engine.css",
    "img/logo.png",
]

missing = [asset for asset in required_assets if not (static_root / asset).is_file()]

if missing:
    print("Missing critical static assets after collectstatic:", file=sys.stderr)
    for asset in missing:
        print(f" - {static_root / asset}", file=sys.stderr)
    raise SystemExit(1)

if not settings.DEBUG and not (static_root / "staticfiles.json").is_file():
    print(f"Missing manifest file: {static_root / 'staticfiles.json'}", file=sys.stderr)
    raise SystemExit(1)

print("Critical static assets are present.")
