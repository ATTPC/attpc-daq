from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^status/', views.status, name='daq/status'),
    url(r'^add_source/', views.add_data_source, name='daq/add_source'),
    url(r'^ecc/get_state/', views.get_ecc_server_state, name='daq/get_ecc_server_state'),
]