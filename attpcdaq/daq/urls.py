from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.status, name='daq/status'),

    url(r'^sources/add/$', views.AddDataSourceView.as_view(), name='daq/add_source'),
    url(r'^sources/edit/(?P<pk>\d+)$', views.UpdateDataSourceView.as_view(), name='daq/update_source'),
    url(r'^sources/remove/(?P<pk>\d+)$', views.RemoveDataSourceView.as_view(), name='daq/remove_source'),

    url(r'^ecc/add/$', views.AddECCServerView.as_view(), name='daq/add_ecc_server'),
    url(r'^ecc/edit/(?P<pk>\d+)$', views.UpdateECCServerView.as_view(), name='daq/update_ecc_server'),
    url(r'^ecc/remove/(?P<pk>\d+)$', views.RemoveECCServerView.as_view(), name='daq/remove_ecc_server'),
    url(r'^ecc/get_state/(\d+)$', views.ecc_get_state, name='daq/ecc_get_state'),
    url(r'^ecc/get_configs/(\d+)$', views.ecc_get_configs, name='daq/ecc_get_configs'),

    url(r'^data_router/add/$', views.AddDataRouterView.as_view(), name='daq/add_data_router'),
    url(r'^data_router/edit/(?P<pk>\d+)$', views.UpdateDataRouterView.as_view(), name='daq/update_data_router'),
    url(r'^data_router/remove/(?P<pk>\d+)$', views.RemoveDataRouterView.as_view(), name='daq/remove_data_router'),

    url(r'^state/set_all/(\d)$', views.set_state_all, name='daq/set_state_all'),
]