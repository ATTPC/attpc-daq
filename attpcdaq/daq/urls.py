from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^status/$', views.status, name='daq/status'),

    url(r'^sources/$', views.ListDataSourcesView.as_view(), name='daq/data_source_list'),
    url(r'^sources/add/$', views.AddDataSourceView.as_view(), name='daq/add_source'),
    url(r'^sources/edit/(?P<pk>\d+)$', views.UpdateDataSourceView.as_view(), name='daq/update_source'),
    url(r'^sources/remove/(?P<pk>\d+)$', views.RemoveDataSourceView.as_view(), name='daq/remove_source'),
    url(r'^sources/get_state/$', views.source_get_state, name='daq/source_get_state'),
    url(r'^sources/change_state/$', views.source_change_state, name='daq/source_change_state'),

    url(r'^ecc/$', views.ListECCServersView.as_view(), name='daq/ecc_server_list'),
    url(r'^ecc/add/$', views.AddECCServerView.as_view(), name='daq/add_ecc_server'),
    url(r'^ecc/edit/(?P<pk>\d+)$', views.UpdateECCServerView.as_view(), name='daq/update_ecc_server'),
    url(r'^ecc/remove/(?P<pk>\d+)$', views.RemoveECCServerView.as_view(), name='daq/remove_ecc_server'),
    url(r'^ecc/get_configs/(\d+)$', views.ecc_get_configs, name='daq/ecc_get_configs'),

    url(r'^data_router/$', views.ListDataRoutersView.as_view(), name='daq/data_router_list'),
    url(r'^data_router/add/$', views.AddDataRouterView.as_view(), name='daq/add_data_router'),
    url(r'^data_router/edit/(?P<pk>\d+)$', views.UpdateDataRouterView.as_view(), name='daq/update_data_router'),
    url(r'^data_router/remove/(?P<pk>\d+)$', views.RemoveDataRouterView.as_view(), name='daq/remove_data_router'),

    url(r'^runs/$', views.ListRunMetadataView.as_view(), name='daq/run_list'),
]
