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
from ..forms import DataSourceForm, ECCServerForm, RunMetadataForm, DataRouterForm, ObservableForm

import json

import logging
logger = logging.getLogger(__name__)


@login_required
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

    experiment = get_object_or_404(Experiment, user=request.user)
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


class ListDataSourcesView(LoginRequiredMixin, ListView):
    """List all data sources."""
    model = DataSource
    queryset = DataSource.objects.order_by('name')
    template_name = 'daq/data_source_list.html'


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


class ListECCServersView(LoginRequiredMixin, ListView):
    """List all ECC servers."""
    model = ECCServer
    queryset = ECCServer.objects.order_by('name')
    template_name = 'daq/ecc_server_list.html'


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


class ListDataRoutersView(LoginRequiredMixin, ListView):
    """List all data routers."""
    model = DataRouter
    queryset = DataRouter.objects.order_by('name')
    template_name = 'daq/data_router_list.html'


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


class UpdateLatestRunMetadataView(RedirectView):
    """Redirects to :class:`UpdateRunMetadataView` for the latest run."""
    pattern_name = 'daq/update_run_metadata'
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        latest_run_pk = RunMetadata.objects.latest('start_datetime').pk
        return super().get_redirect_url(pk=latest_run_pk)


# ----------------------------------------------------------------------------------------------------------------------


class ListObservablesView(LoginRequiredMixin, ListView):
    """List the observables registered for this experiment."""
    model = Observable
    template_name = 'daq/observable_list.html'

    def get_queryset(self):
        """Filter the queryset based on the experiment."""
        expt = get_object_or_404(Experiment, user=self.request.user)
        return Observable.objects.filter(experiment=expt)


class AddObservableView(LoginRequiredMixin, PanelTitleMixin, CreateView):
    """Add a new observable to the experiment."""
    model = Observable
    form_class = ObservableForm
    template_name = 'daq/generic_crispy_form.html'
    panel_title = 'Add an observable'
    success_url = reverse_lazy('daq/observables_list')

    def form_valid(self, form):
        observable = form.save(commit=False)

        experiment = get_object_or_404(Experiment, user=self.request.user)
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
