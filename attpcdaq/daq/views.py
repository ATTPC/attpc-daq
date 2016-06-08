"""AT-TPC DAQ Views

This module contains the main logic of the DAQ controller. The function here are responsible for:
    1) Responding to HTTP requests and returning pages of the website.
    2) Communicating with the ECC servers to configure, start, and stop CoBos.
    3) Adding, editing, and removing objects from the program's internal representation of the DAQ.

"""
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.core.urlresolvers import reverse_lazy
from django.core.serializers import serialize
from django.db.models import Min

from zeep import Client as SoapClient
import xml.etree.ElementTree as ET

from .models import DataSource, ECCServer, DataRouter, ConfigId
from .forms import DataSourceForm, ECCServerForm, DataRouterForm


# ================
# Helper functions
# ================

def _get_soap_client(hostname, ecc_url):
    """Returns the SOAP protocol client object for making ECC server requests.

    Parameters
    ----------
    hostname : str
        The URL of this server. This is used for retrieving the WSDL file.
    ecc_url : str
        The URL of the ECC server to which we want to send a request.

    Returns
    -------
    client : zeep.client.Client
        The SOAP client object for the ECC server.

    """
    wsdl_path = 'http://' + hostname + static('daq/ecc.wsdl')
    client = SoapClient(wsdl_path)
    client.set_address('ecc', 'ecc', ecc_url)
    return client


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
    ecc_server = get_object_or_404(ECCServer, pk=pk)
    client = _get_soap_client(request.get_host(), ecc_server.url)
    result = client.service.GetConfigIDs()

    config_list_xml = ET.fromstring(result.Text)
    config_nodes = [ConfigId.from_xml(s) for s in config_list_xml.findall('ConfigId')]
    for node in config_nodes:
        node.ecc_server = ecc_server
        node.save()

    json_repr = serialize('json', config_nodes)
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

    # Get the ECC server associated with the data source
    try:
        ecc_url = source.ecc_server.url
    except AttributeError:
        return _make_status_response(success=False, error_message="Data source has no ECC server", pk=pk)

    # Make the GetState request
    client = _get_soap_client(request.get_host(), ecc_url)

    try:
        result = client.service.GetState()
    except Exception as e:
        # This would likely be a ConnectionError, indicating that the ECC server is not running.
        current_state = source.state
        trans = False
        success = False
        error_message = str(e)
    else:
        current_state = int(result.State)
        trans = int(result.Transition) == 0
        success = True
        error_message = result.ErrorMessage

    # Update the source's state in the database if needed.
    if source.state != current_state:
        source.state = current_state
        source.save()

    return _make_status_response(success=success, pk=pk, error_message=error_message, state=current_state,
                                 state_name=source.get_state_display(), transitioning=trans)


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

    # Get the information needed for the transition request
    try:
        ecc_url = source.ecc_server.url
    except AttributeError:
        return _make_status_response(success=False, error_message="Data source does not have an ECC server",
                                     pk=pk, state=source.state, state_name=source.get_state_display())

    try:
        config_xml = source.config.as_xml()
    except AttributeError:
        return _make_status_response(success=False, error_message="Data source has no config set",
                                     pk=pk, state=source.state, state_name=source.get_state_display())

    try:
        datalink_xml = source.get_data_link_xml()
    except AttributeError:
        return _make_status_response(success=False, error_message="Data source has no data router",
                                     pk=pk, state=source.state, state_name=source.get_state_display())

    # Create the SOAP service client
    client = _get_soap_client(request.get_host(), ecc_url)

    # Dictionaries of transition functions. Dictionary key is *target* state.
    if source.state < target_state:  # This will be a forward transition
        transition_dict = {
            DataSource.DESCRIBED: client.service.Describe,
            DataSource.PREPARED: client.service.Prepare,
            DataSource.READY: client.service.Configure,
            DataSource.RUNNING: client.service.Start,
        }
    else:  # This will be a backward transition
        transition_dict = {
            DataSource.READY: client.service.Stop,
            DataSource.PREPARED: client.service.Breakup,
            DataSource.DESCRIBED: client.service.Undo,
            DataSource.IDLE: client.service.Undo,
        }

    # Get the function corresponding to the requested transition
    transition = transition_dict[target_state]

    # Finally, perform the transition
    res = transition(config_xml, datalink_xml)

    return _make_status_response(success=int(res.ErrorCode) == 0, error_message=res.ErrorMessage,
                                 pk=pk, state=source.state, state_name=source.get_state_display(),
                                 transitioning=True)


# =========================================================================================================
# Page views:
#
# These functions render particular parts of the web page. Some pages are instead rendered with the classes
# found later in this module.
# =========================================================================================================

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
    return render(request, 'daq/status.html', {'data_sources': sources,
                                               'system_state': system_state})


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


class AddECCServerView(CreateView):
    """Add an ECC server."""
    model = ECCServer
    form_class = ECCServerForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListECCServersView(ListView):
    """List all ECC servers."""
    model = ECCServer
    template_name = 'daq/ecc_server_list.html'


class UpdateECCServerView(UpdateView):
    """Change parameters on an ECC server."""
    model = ECCServer
    form_class = ECCServerForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveECCServerView(DeleteView):
    """Delete an ECC server."""
    model = ECCServer
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

