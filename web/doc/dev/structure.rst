Structure of the DAQ system
===========================

The AT-TPC DAQ system runs inside a collection of Docker containers. Each of these containers is responsible for running
part of the system. In general, one container corresponds to one process. The responsibilities of each container are
outlined below.

Django application
------------------
**Container/service name:** ``web``

This is the core of the system, and it's the container in which nearly all of the Python code in this application runs.
The main process in this container is the Gunicorn web server, which runs the Django application that will be described
in the next pages of this documentation.

This server responds to any requests for *dynamic* web content. When you click a link to load a page of the DAQ app,
the Django library calls the appropriate functions in the web app to dynamically generate the HTML that will be shown.
This also includes calls to the API that communicates with the ECC servers. These calls are implemented as functions
that get called when certain URLs are requested.

NGINX web server
----------------
**Container/service name:** ``nginx``

NGINX is a commonly used web server. It acts as a front-end to the application. When a URL is requested, NGINX receives
the request first and decides whether the request is for static content or dynamic content. Requests for dynamically
generated content are forwarded to the Gunicorn server described above for further processing. Requests for static
content (such as CSS files, the help pages, and static images) are processed by NGINX itself in order to reduce the
load on the Gunicorn server.

Celery task queue
-----------------
**Container/service name:** ``celery``

Celery is a Python-based, distributed, asynchronous task queue system. It receives messages from Django and schedules
tasks accordingly. This allows asynchronous execution of portions of the web app's code. For example, when you
configure the CoBos, a set of tasks is sent to the Celery server that tell it to perform the configuration.

This is useful for long-running tasks like the configuration commands. If these tasks were executed synchronously inside
the main Django process, the web interface would become unresponsive until the tasks finished. Instead, we execute the
tasks asynchronously in the Celery worker processes and update the GUI later when the tasks are finished.

RabbitMQ message broker
-----------------------
**Container/service name:** ``rabbitmq``

RabbitMQ is a "message broker" that coordinates communication between the main process of the Django application
and the Celery task queue system. It needs to be running, but otherwise it is not particularly interesting from the
perspective of the DAQ system.

PostgreSQL database
-------------------
**Container/service name:** ``db``

This is the database used to store the internal configuration of the web app. This stores things like the IP
addresses of the ECC servers and data routers, the name of the config file to use for each CoBo,
the history of recent runs, and the name of the current experiment.





