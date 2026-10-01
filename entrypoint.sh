#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL..."
until python -c "import psycopg2; psycopg2.connect(host='$DB_HOST', dbname='$DB_NAME', user='$DB_USER', password='$DB_PASSWORD')" 2>/dev/null; do
  echo "   PostgreSQL not ready, retrying in 2s..."
  sleep 2
done
echo "   PostgreSQL is ready!"

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "==> Creating superuser if not exists..."
python manage.py shell -c "
from django.contrib.auth.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@viettravel.vn', 'admin123')
    print('Superuser created: admin / admin123')
else:
    print('Superuser already exists')
"

echo "==> Starting Wagtail (Django) server..."
exec gunicorn travel_erp.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
