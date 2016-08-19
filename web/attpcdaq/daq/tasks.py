"""Celery asynchronous tasks for the daq module."""

from celery import shared_task
from .models import DataSource


@shared_task
def datasource_refresh_state_task(datasource_pk):
    ds = DataSource.objects.get(pk=datasource_pk)
    ds.refresh_state()


@shared_task
def datasource_change_state_task(datasource_pk, target_state):
    ds = DataSource.objects.get(pk=datasource_pk)
    ds.change_state(target_state)