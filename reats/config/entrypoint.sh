#!/bin/sh

# Explicitly set PORT in case EB overrides it
export PORT=8000

# Check if we're in a local Docker Compose environment
if [ "$ENV" = "local" ]; then
    echo "Local environment detected. Checking for PostgreSQL container..."

    if [ "$DATABASE" = "$POSTGRES_DB" ]; then
        echo "Waiting for PostgreSQL at $DB_HOST:$DB_PORT..."

        while ! nc -z $DB_HOST $DB_PORT; do
            sleep 0.1
        done

        echo "PostgreSQL started"
    fi

    # Ensure wait-for-it.sh is only used in local mode
    ./wait-for-it.sh -h db -p 5432
else
    echo "non local environment detected. Skipping PostgreSQL check."
fi

# Django setup
python manage.py flush --no-input
python manage.py collectstatic --no-input
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata */fixtures/*.json

# Start Gunicorn
gunicorn --bind 0.0.0.0:$PORT source.wsgi