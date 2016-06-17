#!/bin/bash

python manage.py migrate
python manage.py collectstatic --noinput

gunicorn attpcdaq.wsgi -b :8000