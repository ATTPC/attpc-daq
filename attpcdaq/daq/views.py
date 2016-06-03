from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.core.urlresolvers import reverse_lazy
from django.db.models import Min

from zeep import Client as SoapClient

from .models import DataSource
from .forms import DataSourceForm


def get_ecc_server_state(request):
    wsdl_path = 'http://' + request.get_host() + static('daq/ecc.wsdl')
    client = SoapClient(wsdl_path)
    result = client.service.GetState()
    return HttpResponse(str(result))


def status(request):
    sources = DataSource.objects.all()
    system_state = sources.aggregate(Min('state'))['state__min']
    return render(request, 'daq/status.html', {'data_sources': sources, 'system_state': system_state})


def set_state_all(request, state):
    for source in DataSource.objects.all():
        source.state = state
        source.save()
    return redirect('daq/status')


class AddDataSourceView(CreateView):
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_source.html'
    success_url = reverse_lazy('daq/status')


class UpdateDataSourceView(UpdateView):
    model = DataSource
    form_class = DataSourceForm
    template_name = 'daq/add_source.html'
    success_url = reverse_lazy('daq/status')


class RemoveDataSourceView(DeleteView):
    model = DataSource
    template_name = 'daq/remove_source.html'
    success_url = reverse_lazy('daq/status')
