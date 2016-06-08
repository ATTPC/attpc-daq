from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, JsonResponse
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


def _get_soap_client(hostname, ecc_url):
    wsdl_path = 'http://' + hostname + static('daq/ecc.wsdl')
    client = SoapClient(wsdl_path)
    client.set_address('ecc', 'ecc', ecc_url)
    return client


def ecc_get_configs(request, pk):
    ecc_server = get_object_or_404(ECCServer, pk=pk)
    client = _get_soap_client(request.get_host(), ecc_server.url)
    result = client.service.GetConfigIDs()

    config_list_xml = ET.fromstring(result.Text)
    config_nodes = [ConfigId.from_xml(s) for s in config_list_xml.findall('ConfigId')]
    for node in config_nodes:
        node.ecc_server = ecc_server
        node.save()

    json_repr = serialize('json', config_nodes)
    return HttpResponse(json_repr)


def ecc_configure(request, pk):
    source = get_object_or_404(DataSource, pk=pk)
    if source.state < DataSource.READY:
        # Placeholder
        source.state = DataSource.READY
        source.save()
    return redirect('daq/status')


def ecc_start(request, pk):
    source = get_object_or_404(DataSource, pk=pk)
    if source.state == DataSource.READY:
        # Placeholder
        source.state = DataSource.RUNNING
        source.save()
        return redirect('daq/status')
    else:
        return HttpResponseBadRequest('Cannot start an ECC server that is not configured.')


def _make_status_response(success=True, pk=None, error_message=None, state=None,
                          state_name=None, transitioning=False):
    output = {
        'success': success,
        'pk': pk,
        'error_message': error_message,
        'state': state,
        'state_name': state_name,
        'transitioning': transitioning,
    }
    return JsonResponse(output)


def source_get_state(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    try:
        pk = request.GET['pk']
    except KeyError:
        resp = _make_status_response(success=False, error_message="No data source pk provided")
        resp.status_code = 400
        return resp

    source = get_object_or_404(DataSource, pk=pk)

    try:
        ecc_url = source.ecc_server.url
    except AttributeError:
        return _make_status_response(success=False, error_message="Data source has no ECC server", pk=pk)

    client = _get_soap_client(request.get_host(), ecc_url)

    try:
        result = client.service.GetState()
    except Exception as e:
        current_state = source.state
        trans = False
        success = False
        error_message = str(e)
    else:
        current_state = int(result.State)
        trans = bool(int(result.Transition))
        success = True
        error_message = result.ErrorMessage

    if source.state != current_state:
        source.state = current_state
        source.save()

    return _make_status_response(success=success, pk=pk, error_message=error_message, state=current_state,
                                 state_name=source.get_state_display(), transitioning=trans)


def source_change_state(request):
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


def status(request):
    sources = DataSource.objects.all()
    system_state = sources.aggregate(Min('state'))['state__min']
    return render(request, 'daq/status.html', {'data_sources': sources,
                                               'system_state': system_state})


def set_state_all(request, state):
    for source in DataSource.objects.all():
        source.state = state
        source.save()
    return redirect('daq/status')


class AddDataSourceView(CreateView):
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListDataSourcesView(ListView):
    model = DataSource
    template_name = 'daq/data_source_list.html'


class UpdateDataSourceView(UpdateView):
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveDataSourceView(DeleteView):
    model = DataSource
    template_name = 'daq/remove_source.html'
    success_url = reverse_lazy('daq/status')


class AddECCServerView(CreateView):
    model = ECCServer
    form_class = ECCServerForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListECCServersView(ListView):
    model = ECCServer
    template_name = 'daq/ecc_server_list.html'


class UpdateECCServerView(UpdateView):
    model = ECCServer
    form_class = ECCServerForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveECCServerView(DeleteView):
    model = ECCServer
    template_name = 'daq/remove_source.html'
    success_url = reverse_lazy('daq/status')


class AddDataRouterView(CreateView):
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class ListDataRoutersView(ListView):
    model = DataRouter
    template_name = 'daq/data_router_list.html'


class UpdateDataRouterView(UpdateView):
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveDataRouterView(DeleteView):
    model = DataRouter
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')

