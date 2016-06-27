# AT-TPC DAQ

This repository holds the new GUI for the AT-TPC DAQ system. This is a [Django](https://www.djangoproject.com/)-based 
web application that provides an interface for the GET software. 

## Building and running

### Docker

The project is set up to be built and run inside of a set of [Docker](https://www.docker.com/) containers. To use it like this,
you will need to first install Docker and the `docker-compose` tool (which should be available by default on the latest
Docker build for Mac). 

### Environment file

Next, create a file called `production.env` and place it in the root directory of the repository. This file provides a set 
of environment variables to the Django app and the Docker containers. Put the following keys into the file:

```
DAQ_IS_PRODUCTION=True         # Tells the system to use the production settings, rather than debug.
POSTGRES_USER=[something]      # A user name for the PostgreSQL database. Set it to something reasonable.
POSTGRES_PASSWORD=[something]  # A secure, random password that you will not likely need to remember.
POSTGRES_DB=attpcdaq           # The name of the database for PostgreSQL
DAQ_SECRET_KEY=[something]     # A secure, *STRONG* random string for Django's cryptography tools.
```
    
(Remove the comments before saving.) The passwords and secret keys should be long, random
strings and should be kept secret.

### Building and running

Now, run the following commands to start up the service:

```bash
docker-compose build
docker-compose up
```
    
The build process will take a few moments as it downloads the required containers from Docker Hub and installs the Python
dependencies. Once that's done, three containers should be up and running:

1. A container running PostgreSQL, probably called `attpcdaq_db_1`. This hosts the DAQ system's internal data, but *not*
the experimental data recorded by the system.
2. A container running NGINX, probably called `attpcdaq_nginx_1`, to host the static resources of the site and to handle requests.
3. A container running Gunicorn, probably called `attpcdaq_web_1`, which runs the Django app itself and provides dynamic content.

The system can be stopped by pressing <kbd>Ctrl</kbd>-<kbd>C</kbd> in the terminal window where you ran `docker-compose`.