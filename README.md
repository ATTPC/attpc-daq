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
dependencies. Once that's done, several containers should be up and running. See the [documentation][docs] for more details.

The system can be stopped by pressing <kbd>Ctrl</kbd>-<kbd>C</kbd> in the terminal window where you ran `docker-compose`.

### Testing

| Branch  | Status  |
|---------|---------|
| master  | [![Build Status](https://travis-ci.org/ATTPC/attpc-daq.svg?branch=master)](https://travis-ci.org/ATTPC/attpc-daq)  |
| develop | [![Build Status](https://travis-ci.org/ATTPC/attpc-daq.svg?branch=develop)](https://travis-ci.org/ATTPC/attpc-daq) |

To run the unit tests for this code, you will need to install it in a Python environment on your computer. After setting up
Python 3.5+ (and, preferably, a virtual environment), you can install all of the required packages by running

```bash
pip install -r web/requirements.txt
```

Finally, run the unit tests with the command

```bash
python manage.py test
```

### Documentation

The project's documentation is built using [Sphinx](http://www.sphinx-doc.org/) from the source files in the directory `web/doc`.

The documentation can be viewed online [here][docs], or viewed within the application by clicking on the "Help" icon in the top-right corner.

[docs]: http://attpc-daq.readthedocs.io/