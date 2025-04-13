#!/bin/sh

if [ "$ENV" = "local" ]; then
    echo "Local environment detected. Waiting for PostgreSQL..."
    ./wait-for-it.sh -h db -p 5432 -t 30 -- echo "PostgreSQL is up"
else
    echo "Non-local environment detected. Skipping PostgreSQL check."
fi

# Django setup
python manage.py flush --no-input
python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata */fixtures/*.json

# Start Gunicorn
gunicorn --bind 0.0.0.0:8000 source.wsgi
