#!/bin/sh
set -e

echo "Waiting for postgres at $DATABASE_HOST:$DATABASE_PORT..."
until python -c "
import psycopg2, os
psycopg2.connect(
    dbname=os.environ['DATABASE_NAME'],
    user=os.environ['DATABASE_USER'],
    password=os.environ['DATABASE_PASSWORD'],
    host=os.environ['DATABASE_HOST'],
    port=os.environ['DATABASE_PORT'],
).close()
" 2>/dev/null; do
    sleep 1
done
echo "Postgres is up."

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Starting Gunicorn..."
exec gunicorn quevesve_back.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
