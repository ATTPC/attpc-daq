from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
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


def ecc_get_state(request, pk):
    ecc_server = get_object_or_404(ECCServer, pk=pk)
    client = _get_soap_client(request.get_host(), ecc_server.url)
    result = client.service.GetState()
    return HttpResponse(str(result))


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
    if source.state < DataSource.CONFIGURED:
        # Placeholder
        source.state = DataSource.CONFIGURED
        source.save()
    return redirect('daq/status')


def ecc_start(request, pk):
    source = get_object_or_404(DataSource, pk=pk)
    if source.state == DataSource.CONFIGURED:
        # Placeholder
        source.state = DataSource.RUNNING
        source.save()
        return redirect('daq/status')
    else:
        return HttpResponseBadRequest('Cannot start an ECC server that is not configured.')


# def ecc_change_state(request, pk, target):
#     source = get_object_or_404(DataSource, pk=pk)
#


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

