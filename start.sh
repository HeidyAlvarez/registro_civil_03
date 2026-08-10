#!/usr/bin/env bash
set -o errexit

python manage.py migrate --no-input
python manage.py seed_initial_data
exec gunicorn core_rc.wsgi:application --bind "0.0.0.0:${PORT}"
