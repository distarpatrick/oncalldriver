#!/usr/bin/env bash
# Render build script: install, collect static files, migrate.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Optional: create the first admin account from environment variables
# (DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_FULL_NAME,
# DJANGO_SUPERUSER_PHONE). Skipped when they are not set or the user exists.
if [[ -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --no-input || echo "Superuser already exists, skipping."
fi
