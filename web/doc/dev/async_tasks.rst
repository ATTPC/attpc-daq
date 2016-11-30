Asynchronous tasks and Celery
=============================

Due to the distributed design of the DAQ system, it's very likely that sometimes a command sent to the system will
take a while to process. This is especially true when communicating with an ECC server if the ECC server is
configuring all of its attached data sources in series. If we decided to send a long-running command to the ECC server
synchronously in the middle of whatever view was responding to the user's HTTP request, the view would block on the
communication until it finished. This would prevent it from updating the GUI, giving the impression that the software
has crashed, and in extreme cases, the browser could even return a timeout error.

To prevent this problem, we process slow commands *asynchronously* with Celery. Instead of directly initiating
communications, the view submits a task to the Celery queue and returns immediately, updating the GUI to indicate that
the task is processing. When the task is completed, some part of the database is generally updated. The GUI is then
updated to reflect the fact that the task has completed when it periodically refreshes itself.

Tasks
-----

The Celery tasks in this application are just Python functions with the ``@shared_task`` decorator. This decorator
registers them with the Celery system as tasks, and it also allows us to set a time limit on them. All of the tasks
are located in the module :mod:`attpcdaq.daq.tasks`.

..  currentmodule:: attpcdaq.daq.tasks

..  rubric:: ECC server interaction

..  autosummary::
    :toctree: generated/

    eccserver_refresh_state_task
    eccserver_refresh_all_task
    eccserver_change_state_task

..  rubric:: Checking remote status

..  autosummary::
    :toctree: generated/

    check_ecc_server_online_task
    check_ecc_server_online_all_task
    check_data_router_status_task
    check_data_router_status_all_task

..  rubric:: File organization

..  autosummary::
    :toctree: generated/

    organize_files_task
    organize_files_all_task


Task scheduling
---------------

Some of the tasks above are best run automatically according to a schedule. Periodic tasks are supported by the
Celery system, and are configured using the ``CELERYBEAT_SCHEDULE`` entry in the :mod:`attpcdaq.settings` module.
This is a dictionary with the format shown in the example below.

..  code-block:: python

    CELERYBEAT_SCHEDULE = {
        'update-state-every-5-sec': {                                 # A descriptive name for the task
            'task': 'attpcdaq.daq.tasks.eccserver_refresh_all_task',  # The dotted name of the task, as a string
            'schedule': timedelta(seconds=5),                         # The interval between runs
        },
    }
