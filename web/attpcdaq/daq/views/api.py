from django.shortcuts import get_object_or_404
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy

from ..models import DataSource, RunMetadata, Experiment
from ..models import ECCError
from ..forms import DataSourceForm, RunMetadataForm
from ..tasks import datasource_change_state_task, organize_files_all_task
from .helpers import get_status, calculate_overall_state

import logging
logger = logging.getLogger(__name__)


# ===============================================================================================
# CRUD Views:
#
# These views are used to create, update, list, and delete the objects contained in the database.
# This is used to render the pages for adding ECC servers, for example.
# ===============================================================================================


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
        logger.error('Received non-GET HTTP request %s', request.method)
        return HttpResponseNotAllowed(['GET'])

    output = get_status(request)

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
        logger.error('Received non-POST request %s', request.method)
        return HttpResponseNotAllowed(['POST'])

    try:
        pk = request.POST['pk']
        target_state = int(request.POST['target_state'])
    except KeyError:
        logger.error('Must provide data source pk and target state')
        return HttpResponseBadRequest("Must provide data source pk and target state")

    source = get_object_or_404(DataSource, pk=pk)

    # Handle "reset" case
    if target_state == DataSource.RESET:
        target_state = max(source.state - 1, DataSource.IDLE)

    # Request the transition
    try:
        source.is_transitioning = True
        source.save()
        datasource_change_state_task.delay(source.pk, target_state)
    except Exception:
        logger.exception('Error while submitting change-state task')

    state = get_status(request)

    return JsonResponse(state)


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
        logger.error('Received non-POST request %s', request.method)
        return HttpResponseNotAllowed(['POST'])

    # Get target state
    try:
        target_state = int(request.POST['target_state'])
    except (KeyError, TypeError):
        logger.exception('Invalid or missing target_state')
        return HttpResponseBadRequest('Invalid or missing target_state')

    # Handle "reset" case
    if target_state == DataSource.RESET:
        overall_state, _ = calculate_overall_state(DataSource.objects.all())
        if overall_state is not None:
            target_state = max(overall_state - 1, DataSource.IDLE)
        else:
            logger.error('Cannot perform reset when overall state is inconsistent')
            return HttpResponseBadRequest('Cannot perform reset when overall state is inconsistent')

    # Handle "start" case
    if target_state == DataSource.RUNNING:
        daq_not_ready = DataSource.objects.exclude(daq_state=DataSource.DAQ_READY).exists()
        if daq_not_ready:
            logger.error('Remote DAQ processes are not ready')
            return HttpResponseBadRequest('Remote DAQ processare are not ready')

    for source in DataSource.objects.all():
        try:
            source.is_transitioning = True
            source.save()
            datasource_change_state_task.delay(source.pk, target_state)
        except (ECCError, ValueError) as err:
            logger.exception('Failed to submit change_state task for data source %s', source.name)

    experiment = get_object_or_404(Experiment, user=request.user)

    is_starting = target_state == DataSource.RUNNING and not experiment.is_running
    is_stopping = target_state == DataSource.READY and experiment.is_running

    if is_starting:
        experiment.start_run()
    elif is_stopping:
        experiment.stop_run()
        run_number = experiment.latest_run.run_number
        organize_files_all_task.delay(experiment.name, run_number)

    output = get_status(request)

    return JsonResponse(output)


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


class UpdateRunMetadataView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Change run metadata"""
    model = RunMetadata
    form_class = RunMetadataForm
    template_name = 'daq/add_or_edit_item.html'
    panel_title = 'Edit run metadata'
    success_url = reverse_lazy('daq/run_list')