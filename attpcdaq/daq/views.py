"""AT-TPC DAQ Views

This module contains the main logic of the DAQ controller. The function here are responsible for:
    1) Responding to HTTP requests and returning pages of the website.
    2) Communicating with the ECC servers to configure, start, and stop CoBos.
    3) Adding, editing, and removing objects from the program's internal representation of the DAQ.

"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse, reverse_lazy
from django.core.serializers import serialize
from django.db.models import Min
from datetime import datetime

from .models import DataSource, DataRouter, ConfigId, RunMetadata, Experiment
from .models import ECCError
from .forms import DataSourceForm, DataRouterForm, ExperimentSettingsForm


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
        The integer identifying the current state of the object with primary key `pk`, if applicable.
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


# =====================================================================================================
# ECC Server Communication:
#
# These views will send requests to the ECC servers to get or change the state of the CoBos, and to get
# a listing of the available configurations. They all return JSON arrays that are used to update the
# status page after completion.
# =====================================================================================================

def ecc_get_configs(request, pk):
    """Fetches the set of configurations from a given ECC server.

    This will send a request to the ECC server identified by primary key `pk` to get
    the configuration list. The list is stored in the database's ConfigId table and
    also returned as a JSON array.

    Parameters
    ----------
    request : HttpRequest
        The Django request object.
    pk : int
        The primary key identifying the ECC server in the database.

    Returns
    -------
    HttpResponse
        The response contains a JSON array of the configurations.

    """
    source = get_object_or_404(DataSource, pk=pk)
    source.refresh_configs()
    config_list = source.configid_set.all()

    json_repr = serialize('json', config_list)
    return JsonResponse(json_repr)


def source_get_state(request):
    """Get the state of a given data source.

    This looks up the data source in the database, sends a request to its ECC server to check it's state,
    and then returns the results as a JSON array.

    Parameters
    ----------
    request : HttpRequest
        The request must be made by GET (not POST), and the parameter `pk` must be included. `pk` is the
        integer primary key of a data source in the database.

    Returns
    -------
    JsonResponse
        The results, as a JSON array. This will contain all keys identified in `_make_status_response`.

    """
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    # Get the data source
    try:
        pk = request.GET['pk']
    except KeyError:
        resp = _make_status_response(success=False, error_message="No data source pk provided")
        resp.status_code = 400
        return resp

    source = get_object_or_404(DataSource, pk=pk)

    try:
        source.refresh_state()
    except Exception as e:
        # This could be a ConnectionError, indicating that the ECC server is not running.
        success = False
        error_message = str(e)
    else:
        success = True
        error_message = ""

    return _make_status_response(success=success, pk=pk, error_message=error_message, state=source.state,
                                 state_name=source.get_state_display(), transitioning=source.is_transitioning)


@login_required
def refresh_state_all(request):
    """Refresh the state of all data sources and return the new states.

    Parameters
    ----------
    request : HttpRequest
        The request object. The method must be GET.

    Returns
    -------
    JsonResponse
        An array of dictionaries containing the results from each data source. The content of each dictionary is
        like that in `source_get_state`.
    """
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    results = []

    for source in DataSource.objects.all():
        try:
            source.refresh_state()
        except Exception as e:
            success = False
            error_message = str(e)
        else:
            success = True
            error_message = ""

        source_res = {
            'success': success,
            'pk': source.pk,
            'error_message': error_message,
            'state': source.state,
            'state_name': source.get_state_display(),
            'transitioning': source.is_transitioning,
        }

        results.append(source_res)

    return JsonResponse({'results': results})


def source_change_state(request):
    """Tells the ECC server to change a source's state.

    This view handles all state changes. These state changes are how the CoBo is configured.
    One should probably call `source_get_state` some time after calling this view to check if the
    state change succeeded.

    Parameters
    ----------
    request : HttpRequest
        The request must include the primary key `pk` of the data source and the integer `target_state`
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
        target_state = request.POST['target_state']
    except KeyError:
        resp = _make_status_response(success=False,
                                     error_message="Must provide data source pk and target state")
        resp.status_code = 400
        return resp

    source = get_object_or_404(DataSource, pk=pk)

    # Cast the target_state to an integer for comparisons
    if not isinstance(target_state, int):
        target_state = int(target_state)

    # If the target = the current state, no transition is needed
    if source.state == target_state:
        return _make_status_response(success=True, pk=pk, state=source.state,
                                     state_name=source.get_state_display(), transitioning=False)

    # Request the transition
    try:
        source.change_state(target_state)
    except ECCError as err:
        success = False
        error_message = str(err)
    else:
        success = True
        error_message = ""

    return _make_status_response(success=success, error_message=error_message,
                                 pk=pk, state=source.state, state_name=source.get_state_display(),
                                 transitioning=source.is_transitioning)


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
    sources = DataSource.objects.all()
    system_state = sources.aggregate(Min('state'))['state__min']

    experiment = get_object_or_404(Experiment, user=request.user)
    latest_run = experiment.latest_run

    return render(request, 'daq/status.html', {'data_sources': sources,
                                               'latest_run': latest_run,
                                               'experiment': experiment,
                                               'system_state': system_state})


@login_required
def experiment_settings(request):

    experiment = get_object_or_404(Experiment, user=request.user)

    if request.method == 'POST':
        form = ExperimentSettingsForm(request.POST, instance=experiment)
        form.save()
        return redirect(reverse('daq/experiment_settings'))
    else:
        form = ExperimentSettingsForm(instance=experiment)
        return render(request, 'daq/experiment_settings.html', {'form': form})


# ============
# Internal API
# ============

@login_required
def start_run(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    experiment = get_object_or_404(Experiment, user=request.user)
    if not experiment.is_running:
        new_run = RunMetadata.objects.create(experiment=experiment,
                                             run_number=experiment.next_run_number,
                                             start_datetime=datetime.now())
        new_run.save()

        return _make_runcontrol_response(success=True, start_time=new_run.start_datetime, run_number=new_run.run_number)
    else:
        return JsonResponse({})


@login_required
def stop_run(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    experiment = get_object_or_404(Experiment, user=request.user)
    if experiment.is_running:
        current_run = experiment.latest_run
        current_run.stop_datetime = datetime.now()
        current_run.save()

        return _make_runcontrol_response(success=True, start_time=current_run.start_datetime, run_number=current_run.run_number)
    else:
        return JsonResponse({})

# ===============================================================================================
# CRUD Views:
#
# These views are used to create, update, list, and delete the objects contained in the database.
# This is used to render the pages for adding ECC servers, for example.
# ===============================================================================================


class AddDataSourceView(CreateView):
    """Add a data source."""
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListDataSourcesView(ListView):
    """List all data sources."""
    model = DataSource
    template_name = 'daq/data_source_list.html'


class UpdateDataSourceView(UpdateView):
    """Change parameters on a data source."""
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveDataSourceView(DeleteView):
    """Delete a data source."""
    model = DataSource
    template_name = 'daq/remove_source.html'
    success_url = reverse_lazy('daq/status')


class AddDataRouterView(CreateView):
    """Add a data router."""
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListDataRoutersView(ListView):
    """List all data routers."""
    model = DataRouter
    template_name = 'daq/data_router_list.html'


class UpdateDataRouterView(UpdateView):
    """Change parameters of a data router."""
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveDataRouterView(DeleteView):
    """Delete a data router."""
    model = DataRouter
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListRunMetadataView(ListView):
    """List the run information for all runs."""
    model = RunMetadata
    template_name = 'daq/run_metadata_list.html'


class UpdateExperimentView(UpdateView):
    """Update experiment settings"""
    model = Experiment
    form_class = ExperimentSettingsForm
    template_name = 'daq/experiment_settings.html'
