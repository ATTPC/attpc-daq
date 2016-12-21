# Dockerfile for the Django service
FROM python:3.5

# Make the app directory and change to it
RUN mkdir -p /usr/src/app
WORKDIR /usr/src/app

# Install Python libraries and dependencies
COPY requirements.txt /usr/src/app/
RUN pip install --no-cache-dir -r requirements.txt

# Install Node.js and frontend dependencies
RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && apt-get install -y nodejs
COPY package.json /usr/src/app
RUN npm install -g grunt-cli && npm install

# Copy app files
COPY . /usr/src/app

# Build frontend
RUN grunt

# The command to run is listed in the Docker compose file.
