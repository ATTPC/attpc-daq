"""API views

This module contains views to manipulate database objects. It also contains
the views that respond to AJAX requests from the front end. This includes the
views that control refreshing the state of the system and changing the state.

"""

from django.shortcuts import get_object_or_404
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest, JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.views.generic import RedirectView
from django.core.urlresolvers import reverse_lazy

from ..models import DataSource, ECCServer, DataRouter, RunMetadata, Experiment, Observable
from ..models import ECCError
from ..forms import DataSourceForm, ECCServerForm, RunMetadataForm, DataRouterForm, ObservableForm, NewExperimentForm
from ..tasks import eccserver_change_state_task, organize_files_all_task, backup_config_files_all_task
from .helpers import get_status, calculate_overall_state
from ..middleware import needs_experiment, NeedsExperimentMixin

import json

import logging
logger = logging.getLogger(__name__)


@login_required
@needs_experiment
def refresh_state_all(request):
    """Fetch the state of all data sources from the database and return the overall state of the system.

    The value of the data source state that will be returned is whatever the database says. These values will be
    returned along with the overall state of the system and some information about the current experiment and run.

    ..  note::

        This function does *not* communicate with the ECC server in any way. To contact the ECC server and update
        the state stored in the database, call :meth:`attpcdaq.daq.models.ECCServer.refresh_state` instead.

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
@needs_experiment
def source_change_state(request):
    """Submits a request to tell the ECC server to change a source's state.

    The transition request is put in the Celery task queue.

    Parameters
    ----------
    request : HttpRequest
        The request must include the primary key ``pk`` of the ECC server and the integer ``target_state``
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
        logger.error('Must provide ECC server pk and target state')
        return HttpResponseBadRequest("Must provide ECC server pk and target state")

    ecc_server = get_object_or_404(ECCServer, pk=pk)

    # Handle "reset" case
    if target_state == ECCServer.RESET:
        target_state = max(ecc_server.state - 1, ECCServer.IDLE)

    # Request the transition
    try:
        ecc_server.is_transitioning = True
        ecc_server.save()
        eccserver_change_state_task.delay(ecc_server.pk, target_state)
    except Exception:
        logger.exception('Error while submitting change-state task')

    state = get_status(request)

    return JsonResponse(state)


@login_required
@needs_experiment
def source_change_state_all(request):
    """Send requests to change the state of all ECC servers.

    The requests are queued to be performed asynchronously.

    Parameters
    ----------
    request : HttpRequest
        The request method must be POST, and it must contain an integer representing the target state.

    Returns
    -------
    JsonResponse
        A JSON array containing status information about all ECC servers.

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
    if target_state == ECCServer.RESET:
        overall_state, _ = calculate_overall_state(request)
        if overall_state is not None:
            target_state = max(overall_state - 1, ECCServer.IDLE)
        else:
            logger.error('Cannot perform reset when overall state is inconsistent')
            return HttpResponseBadRequest('Cannot perform reset when overall state is inconsistent')

    # Handle "start" case
    if target_state == ECCServer.RUNNING:
        daq_not_ready = DataRouter.objects.exclude(staging_directory_is_clean=True).exists()
        if daq_not_ready:
            logger.error('Data routers are not ready')
            return HttpResponseBadRequest('Data routers are not ready')

    for ecc_server in ECCServer.objects.filter(experiment=request.experiment):
        try:
            ecc_server.is_transitioning = True
            ecc_server.save()
            eccserver_change_state_task.delay(ecc_server.pk, target_state)
        except (ECCError, ValueError):
            logger.exception('Failed to submit change_state task for ECC server %s', ecc_server.name)

    experiment = request.experiment

    is_starting = target_state == ECCServer.RUNNING and not experiment.is_running
    is_stopping = target_state == ECCServer.READY and experiment.is_running

    if is_starting:
        experiment.start_run()
    elif is_stopping:
        experiment.stop_run()
        organize_files_all_task.delay(experiment.pk, experiment.latest_run.pk)
        backup_config_files_all_task.delay(experiment.pk, experiment.latest_run.pk)

    output = get_status(request)

    return JsonResponse(output)


@login_required
@needs_experiment
def set_observable_ordering(request):
    """An AJAX request that sets the order in which observables are displayed.

    The request should be submitted via POST, and the request body should be JSON encoded. The content should be
    be dictionary with the key "new_order" mapped to a list of Observable primary keys in the desired order.

    Parameters
    ----------
    request : HttpRequest
        The request with the information given above. Must be POST.

    Returns
    -------
    JsonResponse
        If successful, the JSON data ``{'success': True}`` is returned.

    """
    if request.method != 'POST':
        logger.error('Received non-POST request %s', request.method)
        return HttpResponseNotAllowed(['POST'])

    try:
        encoding = request.encoding or 'utf-8'
        json_data = json.loads(request.body.decode(encoding))
        new_order = json_data['new_order']
    except KeyError:
        logger.error('Must include new ordering as key "new_order".')
        return HttpResponseBadRequest('Must include new ordering as key "new_order".')

    try:
        new_order = [int(i) for i in new_order]
    except (TypeError, ValueError):
        logger.exception('Provided ordering was invalid')
        return HttpResponseBadRequest('Provided ordering was invalid')

    experiment = request.experiment
    observables = Observable.objects.filter(experiment=experiment)

    for i, pk in enumerate(new_order):
        obs = observables.get(pk=pk)
        obs.order = i
        obs.save()

    return JsonResponse({'success': True})


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


# ----------------------------------------------------------------------------------------------------------------------


class AddDataSourceView(LoginRequiredMixin, PanelTitleMixin, CreateView):
    """Add a data source."""
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'New data source'
    success_url = reverse_lazy('daq/data_source_list')


class ListDataSourcesView(LoginRequiredMixin, NeedsExperimentMixin, ListView):
    """List all data sources."""
    model = DataSource
    template_name = 'daq/data_source_list.html'

    def get_queryset(self):
        expt = self.request.experiment
        return DataSource.objects.filter(
            ecc_server__experiment=expt,
            data_router__experiment=expt,
        ).order_by('name')


class UpdateDataSourceView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Change parameters on a data source."""
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Edit data source'
    success_url = reverse_lazy('daq/data_source_list')


class RemoveDataSourceView(LoginRequiredMixin, DeleteView):
    """Delete a data source."""
    model = DataSource
    template_name = 'daq/remove_item.html'
    success_url = reverse_lazy('daq/data_source_list')


# ----------------------------------------------------------------------------------------------------------------------


class AddECCServerView(LoginRequiredMixin, PanelTitleMixin, CreateView):
    """Add an ECC server."""
    model = ECCServer
    form_class = ECCServerForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'New ECC server'
    success_url = reverse_lazy('daq/ecc_server_list')


class ListECCServersView(LoginRequiredMixin, NeedsExperimentMixin, ListView):
    """List all ECC servers."""
    model = ECCServer
    template_name = 'daq/ecc_server_list.html'

    def get_queryset(self):
        expt = self.request.experiment
        return ECCServer.objects.filter(experiment=expt).order_by('name')


class UpdateECCServerView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Modify an ECC server."""
    model = ECCServer
    form_class = ECCServerForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Edit ECC server'
    success_url = reverse_lazy('daq/ecc_server_list')


class RemoveECCServerView(LoginRequiredMixin, DeleteView):
    """Delete an ECC server."""
    model = ECCServer
    template_name = 'daq/remove_item.html'
    success_url = reverse_lazy('daq/ecc_server_list')


# ----------------------------------------------------------------------------------------------------------------------


class AddDataRouterView(LoginRequiredMixin, PanelTitleMixin, CreateView):
    """Add a data router."""
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'New data router'
    success_url = reverse_lazy('daq/data_router_list')


class ListDataRoutersView(LoginRequiredMixin, NeedsExperimentMixin, ListView):
    """List all data routers."""
    model = DataRouter
    template_name = 'daq/data_router_list.html'

    def get_queryset(self):
        expt = self.request.experiment
        return DataRouter.objects.filter(experiment=expt).order_by('name')


class UpdateDataRouterView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Modify a data router."""
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Edit data router'
    success_url = reverse_lazy('daq/data_router_list')


class RemoveDataRouterView(LoginRequiredMixin, DeleteView):
    """Delete a data router."""
    model = DataRouter
    template_name = 'daq/remove_item.html'
    success_url = reverse_lazy('daq/data_router_list')


# ----------------------------------------------------------------------------------------------------------------------

class AddExperimentView(LoginRequiredMixin, CreateView):
    """Create a new experiment."""
    model = Experiment
    template_name = 'daq/choose_experiment.html'
    form_class = NewExperimentForm
    success_url = reverse_lazy('daq/status')

# ----------------------------------------------------------------------------------------------------------------------

class ListRunMetadataView(LoginRequiredMixin, NeedsExperimentMixin, ListView):
    """List the run information for all runs."""
    model = RunMetadata
    template_name = 'daq/run_metadata_list.html'

    def get_queryset(self):
        """Filter the queryset based on the Experiment, and sort by run number."""
        expt = self.request.experiment
        return RunMetadata.objects.filter(experiment=expt).order_by('run_number')


class UpdateRunMetadataView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Change run metadata"""
    model = RunMetadata
    form_class = RunMetadataForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Edit run metadata'
    success_url = reverse_lazy('daq/run_list')
    automatic_fields = ['run_number', 'config_name', 'start_datetime', 'stop_datetime']  # Don't prepopulate these

    def get_initial(self):
        initial = super().get_initial()
        should_prepopulate = self.request.GET.get('prepopulate', False)
        if should_prepopulate:
            try:
                this_run = self.get_object()
                prev_run = RunMetadata.objects                          \
                    .filter(start_datetime__lt=this_run.start_datetime) \
                    .latest('start_datetime')

                for field in filter(lambda x: x not in self.automatic_fields, self.form_class.Meta.fields):
                    initial[field] = getattr(prev_run, field)

                prev_measurements = prev_run.measurement_set.all().select_related('observable')
                for measurement in prev_measurements:
                    initial[measurement.observable.name] = measurement.value

            except RunMetadata.DoesNotExist:
                logger.error('No previous run to get values from.')

        return initial


class UpdateLatestRunMetadataView(NeedsExperimentMixin, RedirectView):
    """Redirects to :class:`UpdateRunMetadataView` for the latest run."""
    pattern_name = 'daq/update_run_metadata'
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        latest_run_pk = RunMetadata.objects.filter(experiment=self.request.experiment).latest('start_datetime').pk
        return super().get_redirect_url(pk=latest_run_pk)


# ----------------------------------------------------------------------------------------------------------------------


class ListObservablesView(LoginRequiredMixin, NeedsExperimentMixin, ListView):
    """List the observables registered for this experiment."""
    model = Observable
    template_name = 'daq/observable_list.html'

    def get_queryset(self):
        """Filter the queryset based on the experiment."""
        expt = self.request.experiment
        return Observable.objects.filter(experiment=expt)


class AddObservableView(LoginRequiredMixin, NeedsExperimentMixin, PanelTitleMixin, CreateView):
    """Add a new observable to the experiment."""
    model = Observable
    form_class = ObservableForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Add an observable'
    success_url = reverse_lazy('daq/observables_list')

    def form_valid(self, form):
        observable = form.save(commit=False)

        experiment = self.request.experiment
        observable.experiment = experiment
        return super().form_valid(form)


class UpdateObservableView(LoginRequiredMixin, PanelTitleMixin, UpdateView):
    """Change properties of an Observable."""
    model = Observable
    form_class = ObservableForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Edit an observable'
    success_url = reverse_lazy('daq/observables_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['disabled_fields'] = ['value_type']
        return kwargs


class RemoveObservableView(LoginRequiredMixin, DeleteView):
    """Remove an observable from this experiment."""
    model = Observable
    template_name = 'daq/remove_item.html'
    success_url = reverse_lazy('daq/observables_list')
