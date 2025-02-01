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
pwd
ls -la /usr/src/app/reats/cooker_app
python manage.py flush --no-input
python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata */fixtures/*.json
gunicorn source.wsgi