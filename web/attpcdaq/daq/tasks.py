"""Celery asynchronous tasks for the daq module."""

from celery import shared_task, group
from .models import DataSource
from .workertasks import WorkerInterface

import logging
logger = logging.getLogger(__name__)


@shared_task
def datasource_refresh_state_task(datasource_pk):
    """Fetch the state of a data source from the ECC server.

    Parameters
    ----------
    datasource_pk : int
        The integer primary key of the DataSource object in the database.

    """
    try:
        ds = DataSource.objects.get(pk=datasource_pk)
        ds.refresh_state()
    except Exception:
        logger.exception('Failed to refresh state of source with pk %d', datasource_pk)


@shared_task
def datasource_refresh_all_task():
    """Fetch the state of all data sources from their respective ECC servers.

    This calls `datasource_refresh_state` for each source in the database.

    """
    try:
        pk_list = [ds.pk for ds in DataSource.objects.all()]
        gp = group([datasource_refresh_state_task.s(i) for i in pk_list])
        gp()
    except Exception:
        logger.exception('Failed to refresh state of all data sources')


@shared_task
def datasource_change_state_task(datasource_pk, target_state):
    """Change the state of a data source (make it perform a transition).

    Parameters
    ----------
    datasource_pk : int
        The data source's integer primary key.
    target_state : int
        The target state. Use one of the constants from the DataSource class.

    """
    try:
        ds = DataSource.objects.get(pk=datasource_pk)
        ds.change_state(target_state)
    except Exception:
        logger.exception('Failed to change state of data source with pk %d', datasource_pk)


@shared_task
def organize_files_task(address, experiment_name, run_number):
    """Connects to the DAQ worker nodes to organize files at the end of a run.

    Parameters
    ----------
    address : str
        The IP address of the worker
    experiment_name : str
        The name of the current experiment
    run_number : int
        The most recent run number

    """
    try:
        with WorkerInterface(address) as wint:
            wint.organize_files(experiment_name, run_number)
    except Exception:
        logger.exception('Organize files task failed')
