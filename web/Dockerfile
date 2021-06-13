# Dockerfile for the Django service

# The python-onbuild image automatically copies in the files and installs
# the dependencies listed in requirements.txt.
#FROM python:3.5-onbuild
FROM python:3.7
RUN pip install --upgrade pip
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt
COPY . /usr/src/app
COPY celery_entrypoint.sh /
COPY django_entrypoint.sh /
COPY flower_entrypoint.sh /

# The command to run is listed in the Docker compose file.