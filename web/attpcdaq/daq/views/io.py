"""IO Views

The views in this module process data from the DB to create output files
for downloading. There are also functions to process an uploaded file and
create entries in the database from it.

"""

from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.core import serializers
from django.db import transaction

from ..models import DataSource, RunMetadata, Observable, Measurement
from ..forms import DataSourceListUploadForm
from ..middleware import needs_experiment

import csv

import logging
logger = logging.getLogger(__name__)


@login_required
@needs_experiment
def download_run_metadata(request):
    experiment = request.experiment
    observables = Observable.objects.filter(experiment=experiment)

    run_fields = ['run_number', 'run_class', 'title', 'start_datetime', 'stop_datetime', 'config_name']
    measurement_fields = [obs.name for obs in observables]

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{:s} run metadata.csv"'.format(experiment.name)

    writer = csv.writer(response)
    writer.writerow([RunMetadata._meta.get_field(f).verbose_name for f in run_fields] + measurement_fields)

    for run in RunMetadata.objects.order_by('run_number'):
        measurement_qset = Measurement.objects.filter(run_metadata=run).select_related('observable')
        measurement_dict = {m.observable.name: m.value for m in measurement_qset}

        row_items = [getattr(run, field) for field in run_fields]
        row_items += [measurement_dict[field] for field in measurement_fields]

        writer.writerow(row_items)

    return response


@login_required
def download_datasource_list(request):
    """Create a JSON file listing the configuration of all data sources, and return it as a download.

    Parameters
    ----------
    request : HttpRequest
        The request object

    Returns
    -------
    HttpResponse
        The response contains a JSON file that will be downloaded.
    """
    response = HttpResponse(content_type='application/json')
    response['Content-Disposition'] = 'attachment; filename="data_sources.json"'  # This causes the download behavior

    JSONSerializer = serializers.get_serializer('json')
    serializer = JSONSerializer()

    # Serialize the data directly into the response object, since it's file-like
    serializer.serialize(DataSource.objects.all(), indent=4, stream=response,
                         fields=('name',
                                 'ecc_ip_address',
                                 'ecc_port',
                                 'data_router_ip_address',
                                 'data_router_port',
                                 'data_router_type'))

    return response


@login_required
def upload_datasource_list(request):
    """Reads data source configuration from an attached file and updates the database.

    Note that ALL existing data sources will be removed before adding the new ones. This is, however,
    done atomically, so if the process fails, there should be no change.

    Parameters
    ----------
    request : HttpRequest
        The request object

    Returns
    -------
    HttpResponse
        If successful, redirects to daq/data_source_list.
    """
    if request.method == 'POST':
        form = DataSourceListUploadForm(request.POST, request.FILES)
        if form.is_valid():
            ds_list_serialized = request.FILES['data_source_list']
            ds_list = serializers.deserialize('json', ds_list_serialized)

            # Perform the DB transaction atomically in case the data in the file is invalid
            with transaction.atomic():
                DataSource.objects.all().delete()
                for ds in ds_list:
                    ds.save()

            return redirect(reverse('daq/data_source_list'))
    else:
        form = DataSourceListUploadForm()

    panel_title = 'Upload data source list'

    return render(request, 'daq/generic_crispy_form.html', context={'form': form,
                                                                    'panel_title': panel_title})