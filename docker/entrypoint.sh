#!/bin/sh
set -e

python manage.py wait_for_db

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    python manage.py migrate --noinput
fi

# Production on a host without a shell (Render free): the admin account and the demo data are
# created on start. Both are no-ops when already done, so admin edits survive restarts.
python manage.py ensure_superuser
if [ "${SEED_DEMO_DATA:-false}" = "true" ]; then
    python manage.py seed_data --if-empty
fi

exec "$@"
