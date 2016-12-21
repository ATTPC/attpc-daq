# Dockerfile for the Django service

# The python-onbuild image automatically copies in the files and installs
# the dependencies listed in requirements.txt.
FROM python:3.5-onbuild

RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && apt-get install -y nodejs

# The command to run is listed in the Docker compose file.