from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.core.urlresolvers import reverse_lazy
from django.db.models import Min

from zeep import Client as SoapClient

from .models import DataSource, ECCServer, DataRouter
from .forms import DataSourceForm, ECCServerForm, DataRouterForm


def get_ecc_server_state(request):
    wsdl_path = 'http://' + request.get_host() + static('daq/ecc.wsdl')
    client = SoapClient(wsdl_path)
    result = client.service.GetState()
    return HttpResponse(str(result))


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


def step_state(request):
    pass


def status(request):
    sources = DataSource.objects.all()
    ecc_servers = ECCServer.objects.all()
    data_routers = DataRouter.objects.all()
    system_state = sources.aggregate(Min('state'))['state__min']
    return render(request, 'daq/status.html', {'data_sources': sources,
                                               'ecc_servers': ecc_servers,
                                               'data_routers': data_routers,
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


class UpdateDataRouterView(UpdateView):
    model = DataRouter
    form_class = DataRouterForm
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')


class RemoveDataRouterView(DeleteView):
    model = DataRouter
    template_name = 'daq/add_or_edit_item.html'
    success_url = reverse_lazy('daq/status')

