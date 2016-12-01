"""Main page views

The views in this module render the pages of the web app.

"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import Min
from django.db import transaction

from ..models import DataSource, ECCServer, DataRouter, Experiment
from ..forms import ExperimentSettingsForm, ConfigSelectionForm, EasySetupForm
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

    This renders the :class:`~attpcdaq.daq.forms.ConfigSelectionForm` to pick the configuration.

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
    """Renders the experiment settings page."""

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
        Renders the ``log_file.html`` template with the given log file as content.

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


def _ip_address_generator(first, count):
    components = [int(x) for x in first.split('.')]

    for i in range(count):
        new_ip = '{}.{}.{}.{}'.format(
            components[0],
            components[1],
            components[2],
            components[3] + i
        )
        yield new_ip


def _make_ip(base, index):
    components = [int(x) for x in base.split('.')]
    return '{}.{}.{}.{}'.format(
        components[0],
        components[1],
        components[2],
        components[3] + index
    )


@transaction.atomic
def easy_setup(num_cobos, one_ecc_server, first_cobo_ecc_ip, first_cobo_data_router_ip,
               mutant_is_present, mutant_ecc_ip, mutant_data_router_ip):

    # Clear out old items
    DataSource.objects.all().delete()
    ECCServer.objects.all().delete()
    DataRouter.objects.all().delete()

    # Create CoBo ECC servers
    if one_ecc_server:
        global_ecc = ECCServer.objects.create(
            name='ECC'.format(),
            ip_address=first_cobo_ecc_ip,
        )

    for i in range(num_cobos):
        if one_ecc_server:
            ecc = global_ecc
        else:
            ecc = ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address=_make_ip(first_cobo_ecc_ip, i),
            )

        data_router = DataRouter.objects.create(
            name='DataRouter{}'.format(i),
            ip_address=_make_ip(first_cobo_data_router_ip, i),
            connection_type=DataRouter.TCP,
        )

        DataSource.objects.create(
            name='CoBo[{}]'.format(i),
            ecc_server=ecc,
            data_router=data_router,
        )

    if mutant_is_present:
        if one_ecc_server:
            mutant_ecc = global_ecc
        else:
            mutant_ecc = ECCServer.objects.create(
                name='ECC_mutant',
                ip_address=mutant_ecc_ip,
            )

        mutant_router = DataRouter.objects.create(
            name='DataRouter_mutant',
            ip_address=mutant_data_router_ip,
            connection_type=DataRouter.FDT,
        )

        DataSource.objects.create(
            name='Mutant[master]',
            ecc_server=mutant_ecc,
            data_router=mutant_router,
        )


@login_required
def easy_setup_page(request):

    if request.method == 'POST':
        form = EasySetupForm(request.POST)
        if form.is_valid():
            easy_setup(
                num_cobos=form.cleaned_data['num_cobos'],
                one_ecc_server=form.cleaned_data['one_ecc_server'],
                first_cobo_ecc_ip=form.cleaned_data['first_cobo_ecc_ip'],
                first_cobo_data_router_ip=form.cleaned_data['first_cobo_data_router_ip'],
                mutant_is_present=form.cleaned_data['mutant_is_present'],
                mutant_ecc_ip=form.cleaned_data['mutant_ecc_ip'],
                mutant_data_router_ip=form.cleaned_data['mutant_data_router_ip'],
            )

    else:
        form = EasySetupForm()

    return
