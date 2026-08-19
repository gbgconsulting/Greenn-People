#!/bin/sh
set -e

# Apply migrations before starting the process (web / worker / beat).
python manage.py migrate --noinput

exec "$@"
