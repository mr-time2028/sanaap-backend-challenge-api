#!/bin/sh
# Apply database migrations on every start, then hand over to the CMD.
python manage.py migrate --noinput
exec "$@"
