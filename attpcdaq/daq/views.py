from django.shortcuts import render
from django.http import HttpResponse
from django.contrib.staticfiles.templatetags.staticfiles import static

from zeep import Client as SoapClient

from .models import DataSource
from .forms import AddDataSourceForm


def get_ecc_server_state(request):
    wsdl_path = 'http://' + request.get_host() + static('daq/ecc.wsdl')
    client = SoapClient(wsdl_path)
    result = client.service.GetState()
    return HttpResponse(str(result))


def status(request):
    sources = DataSource.objects.all()
    return render(request, 'daq/status.html', {'data_sources': sources})


def add_data_source(request):
    form = AddDataSourceForm()
    return render(request, 'daq/add_source.html', {'form': form})
