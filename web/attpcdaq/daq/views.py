"""AT-TPC DAQ Views

This module contains code that renders the pages of the web app and serves as an interface for requesting
actions from the DAQ.

"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse, reverse_lazy
from django.db.models import Min
from .workertasks import WorkerInterface

from .models import DataSource, RunMetadata, Experiment
from .models import ECCError
from .forms import DataSourceForm, ExperimentSettingsForm, ConfigSelectionForm
from .tasks import datasource_refresh_state_task, datasource_change_state_task


# ================
# Helper functions
# ================

def _make_status_response(success=True, pk=None, error_message=None, state=None,
                          state_name=None, transitioning=False):
    """A helper function to generate a JSON response for the main status page.

    Parameters
    ----------
    success : bool, optional
        Did the request succeed?
    pk : int, optional
        The primary key of the object associated with the request.
    error_message : str, optional
        An error message to display, if applicable.
    state : int, optional
        The integer identifying the current state of the object with primary key ``pk``, if applicable.
    state_name : str, optional
        The display name of the state.
    transitioning : bool, optional
        Is the system undergoing a transition?

    Returns
    -------
    JsonResponse
        Contains a JSON array of the above keys.

    """
    output = {
        'success': success,
        'pk': pk,
        'error_message': error_message,
        'state': state,
        'state_name': state_name,
        'transitioning': transitioning,
    }
    return JsonResponse(output)


def _make_runcontrol_response(success, run_number=None, start_time=None, error_message=None):
    output = {
        'success': success,
        'run_number': run_number,
        'start_time': start_time,
        'error_message': error_message,
    }
    return JsonResponse(output)


def _calculate_overall_state(source_list):
    """Find the overall state of the system.

    Parameters
    ----------
    source_list : QuerySet
        A set of DataSource objects.

    Returns
    -------
    overall_state : int or None
        The overall state of the system. Returns ``None`` if the state is mixed.
    overall_state_name : str
        The name of the system state. The value 'Mixed' is returned if the system is not in a
        consistent state.

    """
    if len(set(s.state for s in source_list)) == 1:
        # All states are the same
        overall_state = source_list.first().state
        overall_state_name = source_list.first().get_state_display()
    else:
        overall_state = None
        overall_state_name = 'Mixed'

    return overall_state, overall_state_name


# =====================================================================================================
# ECC Server Communication:
#
# These views will send requests to the ECC servers to get or change the state of the CoBos, and to get
# a listing of the available configurations. They all return JSON arrays that are used to update the
# status page after completion.
# =====================================================================================================

@login_required
def refresh_state_all(request):
    """Fetch the state of all data sources and return the overall state of the system.

    The value of the data source state that will be returned is whatever the database says. These values will be
    returned along with the overall state of the system and some information about the current experiment and run.

    The JSON array returned will contain the following keys:

    overall_state
        The overall state of the system. If all of the data sources have the same state, this should
        be the numerical ID of a state. If the sources have different states, it should be -1.
    overall_state_name
        The name of the overall state of the system. Either a state name or "Mixed" if the state
        is inconsistent.
    run_number
        The current run number.
    start_time
        The date and time when the current run started.
    run_duration
        The duration of the current run. This is with respect to the current time if the run
        has not ended.
    individual_results
        The results for the individual data sources. These are sub-arrays.

    The sub arrays for the individual results should include the keys:

    success
        Whether the request succeeded.
    pk
        The primary key of the source.
    error_message
        An error message.
    state
        The ID of the current state.
    state_name
        The name of the current state
    transitioning
        Whether the source is undergoing a state transition.

    Parameters
    ----------
    request : HttpRequest
        The request object. The method must be GET.

    Returns
    -------
    JsonResponse
        An array of dictionaries containing the results from each data source. See above for the contents.

    """
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    results = []

    for source in DataSource.objects.all():
        source_res = {
            'success': True,
            'pk': source.pk,
            'error_message': "",
            'state': source.state,
            'state_name': source.get_state_display(),
            'transitioning': source.is_transitioning,
        }

        results.append(source_res)

    overall_state, overall_state_name = _calculate_overall_state(DataSource.objects.all())

    experiment = get_object_or_404(Experiment, user=request.user)
    current_run = experiment.latest_run
    if current_run is not None:
        run_number = current_run.run_number
        start_time = current_run.start_datetime.strftime('%b %d %Y, %H:%M:%S')
        duration_str = current_run.duration_string
    else:
        run_number = None
        start_time = None
        duration_str = None

    output = {
        'overall_state': overall_state,
        'overall_state_name': overall_state_name,
        'individual_results': results,
        'run_number': run_number,
        'start_time': start_time,
        'run_duration': duration_str,
    }
    return JsonResponse(output)


@login_required
def source_change_state(request):
    """Submits a request to tell the ECC server to change a source's state.

    The transition request is put in the Celery task queue.

    Parameters
    ----------
    request : HttpRequest
        The request must include the primary key ``pk`` of the data source and the integer ``target_state``
        to change to. The request must be made via POST.

    Returns
    -------
    JsonResponse
        The JSON response includes the items outlined in `_make_status_response`.

    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    try:
        pk = request.POST['pk']
        target_state = int(request.POST['target_state'])
    except KeyError:
        resp = _make_status_response(success=False,
                                     error_message="Must provide data source pk and target state")
        resp.status_code = 400
        return resp

    source = get_object_or_404(DataSource, pk=pk)

    # Handle "reset" case
    if target_state == DataSource.RESET:
        target_state = max(source.state - 1, DataSource.IDLE)

    # Request the transition
    try:
        datasource_change_state_task.delay(source.pk, target_state)
    except (ECCError, ValueError) as err:
        success = False
        error_message = str(err)
    else:
        success = True
        error_message = ""

    return _make_status_response(success=success, error_message=error_message,
                                 pk=pk, state=source.state, state_name=source.get_state_display(),
                                 transitioning=source.is_transitioning)


@login_required
def source_change_state_all(request):
    """Send requests to change the state of all sources.

    The requests are queued to be performed asynchronously.

    Parameters
    ----------
    request : HttpRequest
        The request method must be POST, and it must contain an integer representing the target state.

    Returns
    -------
    JsonResponse
        A JSON array containing status information about all sources.

    """
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    # Get target state
    try:
        target_state = int(request.POST['target_state'])
    except (KeyError, TypeError):
        resp = _make_status_response(success=False,
                                     error_message="Must provide target state as integer.")
        resp.status_code = 400
        return resp

    # Handle "reset" case
    if target_state == DataSource.RESET:
        overall_state, _ = _calculate_overall_state(DataSource.objects.all())
        if overall_state is not None:
            target_state = max(overall_state - 1, DataSource.IDLE)
        else:
            resp = _make_status_response(success=False,
                                         error_message="Cannot perform reset when overall state is inconsistent.")
            return resp

    results = []
    for source in DataSource.objects.all():
        try:
            source.is_transitioning = True
            source.save()
            datasource_change_state_task.delay(source.pk, target_state)
        except (ECCError, ValueError) as err:
            success = False
            error_message = str(err)
        else:
            success = True
            error_message = ""

        source_result = {
            'success': success,
            'error_message': error_message,
            'pk': source.pk,
            'state': source.state,
            'state_name': source.get_state_display(),
            'transitioning': source.is_transitioning,
        }

        results.append(source_result)

    experiment = get_object_or_404(Experiment, user=request.user)

    is_starting = target_state == DataSource.RUNNING and not experiment.is_running
    is_stopping = target_state == DataSource.READY and experiment.is_running

    if is_starting:
        experiment.start_run()
    elif is_stopping:
        experiment.stop_run()

    current_run = experiment.latest_run
    if current_run is not None:
        run_number = current_run.run_number
        start_datetime = current_run.start_datetime
    else:
        run_number = None
        start_datetime = None

    if is_stopping:
        # Organize the graw files on the data router host
        for source in DataSource.objects.all():
            with WorkerInterface(source.data_router_ip_address) as wint:
                wint.organize_files(experiment.name, run_number)

    overall_state, overall_state_name = _calculate_overall_state(DataSource.objects.all())

    output = {
        'success': all((s['success'] for s in results)),
        'run_number': run_number,
        'start_time': start_datetime,
        'overall_state': overall_state,
        'overall_state_name': overall_state_name,
        'individual_results': results,
    }

    return JsonResponse(output)


# =========================================================================================================
# Page views:
#
# These functions render particular parts of the web page. Some pages are instead rendered with the classes
# found later in this module.
# =========================================================================================================

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
    system_state = sources.aggregate(Min('state'))['state__min']

    experiment = get_object_or_404(Experiment, user=request.user)
    latest_run = experiment.latest_run

    return render(request, 'daq/status.html', {'data_sources': sources,
                                               'latest_run': latest_run,
                                               'experiment': experiment,
                                               'system_state': system_state})


@login_required
def choose_config(request, pk):
    """Renders a page for choosing the config for a DataSource.

    This renders the `attpcdaq.daq.forms.ConfigSelectionForm` to pick the configuration.

    Parameters
    ----------
    request : HttpRequest
        The request object
    pk : int
        The primary key of the data source to configure.

    Returns
    -------
    HttpResponse
        Redirects back to the main page on success.

    """
    source = get_object_or_404(DataSource, pk=pk)

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


# ===============================================================================================
# CRUD Views:
#
# These views are used to create, update, list, and delete the objects contained in the database.
# This is used to render the pages for adding ECC servers, for example.
# ===============================================================================================

class PanelTitleMixin(object):
    """A mixin that provides a panel title to be used in a template.

    This overrides `get_context_data` to insert a key ``panel_title`` containing a title. The title
    can be set in subclasses by setting the class attribute ``panel_title``.

    """
    panel_title = None

    def get_title(self):
        """Get the title by returning `self.panel_title`."""
        return self.panel_title

    def get_context_data(self, **kwargs):
        """Update the context to include a title."""
        context = super().get_context_data(**kwargs)
        context['panel_title'] = self.get_title()
        return context


class AddDataSourceView(LoginRequiredMixin, PanelTitleMixin, CreateView):
    """Add a data source."""
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_or_edit_item.html'
    panel_title = 'New data source'
    success_url = reverse_lazy('daq/data_source_list')


class ListDataSourcesView(LoginRequiredMixin, ListView):
    """List all data sources."""
    model = DataSource
    queryset = DataSource.objects.order_by('name')
    template_name = 'daq/data_source_list.html'


class UpdateDataSourceView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Change parameters on a data source."""
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_or_edit_item.html'
    panel_title = 'Edit data source'
    success_url = reverse_lazy('daq/data_source_list')


class RemoveDataSourceView(LoginRequiredMixin, DeleteView):
    """Delete a data source."""
    model = DataSource
    template_name = 'daq/remove_item.html'
    success_url = reverse_lazy('daq/data_source_list')


class ListRunMetadataView(LoginRequiredMixin, ListView):
    """List the run information for all runs."""
    model = RunMetadata
    template_name = 'daq/run_metadata_list.html'

    def get_queryset(self):
        """Filter the queryset based on the Experiment, and sort by run number."""
        expt = get_object_or_404(Experiment, user=self.request.user)
        return RunMetadata.objects.filter(experiment=expt).order_by('run_number')

