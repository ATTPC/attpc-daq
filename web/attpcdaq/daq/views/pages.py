"""Main page views

The views in this module render the pages of the web app.

"""

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Min
from django.db import transaction
from django.views.generic.edit import FormView

from ..models import DataSource, ECCServer, DataRouter, Experiment, RunMetadata, Observable, Measurement
from ..forms import ExperimentForm, ConfigSelectionForm, EasySetupForm, ExperimentChoiceForm
from ..workertasks import WorkerInterface
from .helpers import needs_experiment, get_current_experiment

from attpcdaq.logs.models import LogEntry

import logging
logger = logging.getLogger(__name__)


@login_required
@needs_experiment
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
    experiment = get_current_experiment(request)
    latest_run = experiment.latest_run

    sources = DataSource.objects.filter(
        ecc_server__experiment=experiment,
        data_router__experiment=experiment,
    ).order_by('name')
    ecc_servers = ECCServer.objects.filter(experiment=experiment).order_by('name')
    data_routers = DataRouter.objects.filter(experiment=experiment).order_by('name')
    system_state = ECCServer.objects.all().aggregate(Min('state'))['state__min']

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
        return render(request, 'daq/generic_crispy_form.html', context={
            'form': form,
            'panel_title': 'Choose configuration file set'
        })


@login_required
@needs_experiment
def experiment_settings(request):
    """Renders the experiment settings page."""

    experiment = get_current_experiment(request)

    if request.method == 'POST':
        form = ExperimentForm(request.POST, instance=experiment)
        form.save()
        return redirect(reverse('daq/experiment_settings'))
    else:
        form = ExperimentForm(instance=experiment)
        return render(request, 'daq/experiment_settings.html', {'form': form})


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
    if program == 'ecc':
        ecc = get_object_or_404(ECCServer, pk=pk)
        path = ecc.log_path
        ip_address = ecc.ip_address
    elif program == 'data_router':
        dr = get_object_or_404(DataRouter, pk=pk)
        path = dr.log_path
        ip_address = dr.ip_address
    else:
        logger.error('Cannot show log for program %s', program)
        return HttpResponseBadRequest('Bad program name')

    with WorkerInterface(ip_address) as wint:
        log_content = wint.tail_file(path)

    return render(request, 'daq/log_file.html', context={'log_content': log_content})


def _make_ip(base, offset):
    """Generate an IP address with an offset from the given base address.

    This will add the given offset to the last part of the base address.

    Parameters
    ----------
    base : str
        The base address, to which the offset will be added.
    offset : int
        The offset to add to the last component of the base.

    Examples
    --------
    >>> _make_ip('192.168.1.10', 5)
    '192.168.1.15'
    >>> _make_ip('10.0.1.20', 15)
    '10.0.1.35'
    """
    components = [int(x) for x in base.split('.')]
    return '{}.{}.{}.{}'.format(
        components[0],
        components[1],
        components[2],
        components[3] + offset
    )


@transaction.atomic
def easy_setup(experiment, num_cobos, one_ecc_server, first_cobo_ecc_ip, first_cobo_data_router_ip,
               mutant_is_present=False, mutant_ecc_ip=None, mutant_data_router_ip=None):
    """Create a set of model instances with default values based on the given parameters.

    This will populate the database with all of the required DAQ components. Note that all old instances will
    be deleted. This is done atomically, so if this function fails, nothing will be changed.

    Parameters
    ----------
    num_cobos : int
        The number of CoBos to add to the system.
    one_ecc_server : bool
        If True, all data sources will use the same ECC server. If False, a separate ECC server will be created
        for each data source.
    first_cobo_ecc_ip : str
        The IP address of the ECC server for the first CoBo. Subsequent ECC servers will have IP addresses whose
        last component is incremented by one.
    first_cobo_data_router_ip : str
        The IP address of the data router for the first CoBo. Subsequent data routers will have IP addresses whose
        last component is incremented by one.
    mutant_is_present : bool, optional
        True if the MuTAnT is present in the system and should be set up.
    mutant_ecc_ip : str, optional
        The IP address of the ECC server of the MuTAnT. This will be overridden if `one_ecc_server` is True.
    mutant_data_router_ip : str, optional
        The IP address of the data router of the MuTAnT.
    """
    # Clear out old items
    DataSource.objects.filter(ecc_server__experiment=experiment, data_router__experiment=experiment).delete()
    ECCServer.objects.filter(experiment=experiment).delete()
    DataRouter.objects.filter(experiment=experiment).delete()

    # Create CoBo ECC servers
    if one_ecc_server:
        global_ecc = ECCServer.objects.create(
            name='ECC'.format(),
            ip_address=first_cobo_ecc_ip,
            experiment=experiment,
        )

    for i in range(num_cobos):
        if one_ecc_server:
            ecc = global_ecc
        else:
            ecc = ECCServer.objects.create(
                name='ECC{}'.format(i),
                ip_address=_make_ip(first_cobo_ecc_ip, i),
                experiment=experiment,
            )

        data_router = DataRouter.objects.create(
            name='DataRouter{}'.format(i),
            ip_address=_make_ip(first_cobo_data_router_ip, i),
            connection_type=DataRouter.TCP,
            experiment=experiment,
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
                experiment=experiment,
            )

        mutant_router = DataRouter.objects.create(
            name='DataRouter_mutant',
            ip_address=mutant_data_router_ip,
            connection_type=DataRouter.FDT,
            experiment=experiment,
        )

        DataSource.objects.create(
            name='Mutant[master]',
            ecc_server=mutant_ecc,
            data_router=mutant_router,
        )


@login_required
@needs_experiment
def easy_setup_page(request):
    """Renders the easy setup form for one-step system configuration.

    The actual changes to the database are made by :func:`easy_setup`.

    Parameters
    ----------
    request : HttpRequest
        The request.

    Returns
    -------
    HttpResponse
        Renders the form. Redirects to the status page on success.
    """
    if request.method == 'POST':
        form = EasySetupForm(request.POST)
        experiment = get_current_experiment(request)
        if form.is_valid():
            easy_setup(
                experiment=experiment,
                num_cobos=form.cleaned_data['num_cobos'],
                one_ecc_server=form.cleaned_data['one_ecc_server'],
                first_cobo_ecc_ip=form.cleaned_data['first_cobo_ecc_ip'],
                first_cobo_data_router_ip=form.cleaned_data['first_cobo_data_router_ip'],
                mutant_is_present=form.cleaned_data['mutant_is_present'],
                mutant_ecc_ip=form.cleaned_data['mutant_ecc_ip'],
                mutant_data_router_ip=form.cleaned_data['mutant_data_router_ip'],
            )

            return redirect(reverse('daq/status'))

    else:
        form = EasySetupForm()

    return render(request, 'daq/generic_crispy_form.html', {'panel_title': 'Easy setup', 'form': form})


@login_required
@needs_experiment
def measurement_chart(request):
    experiment = get_current_experiment(request)
    observables = Observable.objects.filter(experiment=experiment)
    runs = RunMetadata.objects.filter(experiment=experiment)

    all_measurements = {}
    for run in runs:
        measurement_qset = Measurement.objects.filter(run_metadata=run).select_related('observable')
        measurement_dict = {m.observable.name: m.value for m in measurement_qset}
        all_measurements[run.run_number] = measurement_dict

    return render(request, 'daq/measurement_chart.html', context={
        'observables': observables,
        'runs': runs,
        'measurements': all_measurements,
    })


class ExperimentChoiceView(LoginRequiredMixin, FormView):
    form_class = ExperimentChoiceForm
    success_url = reverse_lazy('daq/status')
    template_name = 'daq/choose_experiment.html'

    def form_valid(self, form):
        expt = form.cleaned_data['experiment']
        self.request.session['current_experiment_pk'] = expt.pk
        return super().form_valid(form)
