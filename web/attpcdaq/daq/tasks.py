"""Celery asynchronous tasks for the daq module."""

from celery import shared_task, group
from .models import DataSource


@shared_task
def datasource_refresh_state_task(datasource_pk):
    """Fetch the state of a data source from the ECC server.

    Parameters
    ----------
    datasource_pk : int
        The integer primary key of the DataSource object in the database.

    """
    ds = DataSource.objects.get(pk=datasource_pk)
    ds.refresh_state()


@shared_task
def datasource_refresh_all_task():
    """Fetch the state of all data sources from their respective ECC servers.

    This calls `datasource_refresh_state` for each source in the database.

    """
    pk_list = [ds.pk for ds in DataSource.objects.all()]
    gp = group([datasource_refresh_state_task.s(i) for i in pk_list])
    gp()


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
    ds = DataSource.objects.get(pk=datasource_pk)
    ds.change_state(target_state)