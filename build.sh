#!/usr/bin/env bash
# Render build script: install, collect static files, migrate.
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate --no-input

# Optional: create the first admin account from environment variables
# (DJANGO_SUPERUSER_EMAIL, DJANGO_SUPERUSER_PASSWORD, DJANGO_SUPERUSER_FULL_NAME,
# DJANGO_SUPERUSER_PHONE in +250XXXXXXXXX format). Skipped when they are not set.
if [[ -n "${DJANGO_SUPERUSER_EMAIL:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
  python manage.py createsuperuser --no-input \
    || echo "Admin account not created: it may already exist, or DJANGO_SUPERUSER_PHONE is not in +250XXXXXXXXX format."
fi
