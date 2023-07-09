#!/bin/sh

if [ "$DATABASE" = "$POSTGRES_DB" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

python manage.py flush --no-input
python manage.py migrate
gunicorn --bind 0.0.0.0:8000 source.wsgi