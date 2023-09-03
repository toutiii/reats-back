#!/bin/sh

if [ "$DATABASE" = "$POSTGRES_DB" ]
then
    echo "Waiting for postgres..."

    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done

    echo "PostgreSQL started"
fi

./wait-for-it.sh -h db -p 5432
python manage.py flush --no-input
python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata cookers.json
gunicorn source.wsgi