"""Main page views

The views in this module render the pages of the web app.

"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Min

from ..models import DataSource, ECCServer, DataRouter, Experiment
from ..forms import ExperimentSettingsForm, ConfigSelectionForm
from ..workertasks import WorkerInterface

from attpcdaq.logs.models import LogEntry

import logging
logger = logging.getLogger(__name__)


@login_required
def status(request):
    """Renders the main status page.

    Parameters
    ----------
    request : HttpRequest
        The request object.

    Returns
    -------
    HttpResponse
        The rendered page.

    """
    sources = DataSource.objects.order_by('name')
    ecc_servers = ECCServer.objects.order_by('name')
    data_routers = DataRouter.objects.order_by('name')
    system_state = ECCServer.objects.all().aggregate(Min('state'))['state__min']

    experiment = get_object_or_404(Experiment, user=request.user)
    latest_run = experiment.latest_run

    logs = LogEntry.objects.order_by('-create_time')[:10]

    return render(request, 'daq/status_page/status.html', {
        'data_sources': sources,
        'ecc_servers': ecc_servers,
        'data_routers': data_routers,
        'latest_run': latest_run,
        'experiment': experiment,
        'logentry_list': logs,
        'system_state': system_state
    })


@login_required
def choose_config(request, pk):
    """Renders a page for choosing the config for an ECC server.

    This renders the `attpcdaq.daq.forms.ConfigSelectionForm` to pick the configuration.

    Parameters
    ----------
    request : HttpRequest
        The request object
    pk : int
        The primary key of the ECC server to configure.

    Returns
    -------
    HttpResponse
        Redirects back to the main page on success.

    """
    source = get_object_or_404(ECCServer, pk=pk)

    if request.method == 'POST':
        form = ConfigSelectionForm(request.POST, instance=source)
        form.save()
        return redirect(reverse('daq/status'))
    else:
        source.refresh_configs()
        form = ConfigSelectionForm(instance=source)
        return render(request, 'daq/add_or_edit_item.html', {'form': form})


@login_required
def experiment_settings(request):
    """Renders the experiment settings page.

    Parameters
    ----------
    request : HttpRequest
        The request.

    Returns
    -------
    HttpResponse
        The rendered page.

    """

    experiment = get_object_or_404(Experiment, user=request.user)

    if request.method == 'POST':
        form = ExperimentSettingsForm(request.POST, instance=experiment)
        form.save()
        return redirect(reverse('daq/experiment_settings'))
    else:
        form = ExperimentSettingsForm(instance=experiment)
        return render(request, 'daq/experiment_settings.html', {'form': form})


@login_required
def remote_status(request):
    """Renders a page showing the status of the remote processes (ECC server and data router)."""
    datasource_list = DataSource.objects.all()
    return render(request, 'daq/remote_status.html', context={'datasource_list': datasource_list})


@login_required
def show_log_page(request, pk, program):
    """Retrieve and render the log file for the given program.

    This can be used to display the end of the log file for the ECC server process or the
    data router process.

    Parameters
    ----------
    request : HttpRequest
        The request object.
    pk : int
        The integer primary key of the data source whose logs we want to view.
    program : str
        The program whose logs we want. Must be one of 'ecc' or 'data_router'.

    Returns
    -------
    HttpResponse
        Renders the log_file.html template with the given log file as content.

    """
    ds = get_object_or_404(DataSource, pk=pk)

    if program == 'ecc':
        path = ds.ecc_log_path
    elif program == 'data_router':
        path = ds.data_router_log_path
    else:
        logger.error('Cannot show log for program %s', program)
        return HttpResponseBadRequest('Bad program name')

    with WorkerInterface(ds.ecc_ip_address) as wint:
        log_content = wint.tail_file(path)

    return render(request, 'daq/log_file.html', context={'log_content': log_content})