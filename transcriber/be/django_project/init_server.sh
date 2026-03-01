#! /bin/bash

# Create and update database structure according to migration files
echo Applying server migrations...
python manage.py migrate

# Gather front end files into one location for serving
echo Collecting static files...
python manage.py collectstatic

# Start the server
echo Starting local server...
waitress-serve --host=127.0.0.1 --port=8000 django_project.wsgi:application