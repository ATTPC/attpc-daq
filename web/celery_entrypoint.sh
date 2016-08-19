#!/bin/bash
# This script is the main entrypoint for the Celery task server. It gets executed on launch.
# It begins by checking to see if RabbitMQ is ready.

# Wait for RabbitMQ
if ! python ready.py ${CELERY_BROKER_HOST} ${CELERY_BROKER_PORT}
then
    exit 1  # If we got here, something is wrong.
fi

celery -A attpcdaq worker -B --concurrency 10  # start Celery
