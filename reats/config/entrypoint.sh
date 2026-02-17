#!/bin/sh

# Django setup
python manage.py flush --no-input
python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata */fixtures/*.json
python manage.py init_data

# Start Gunicorn
gunicorn --bind 0.0.0.0:8000 source.wsgi
