from django.conf.urls import include, url
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='daq/status')),
    url(r'^status/$', views.status, name='daq/status'),

    url(r'^sources/$', views.ListDataSourcesView.as_view(), name='daq/data_source_list'),
    url(r'^sources/add/$', views.AddDataSourceView.as_view(), name='daq/add_source'),
    url(r'^sources/edit/(?P<pk>\d+)$', views.UpdateDataSourceView.as_view(), name='daq/update_source'),
    url(r'^sources/remove/(?P<pk>\d+)$', views.RemoveDataSourceView.as_view(), name='daq/remove_source'),
    url(r'^sources/get_state/$', views.source_get_state, name='daq/source_get_state'),
    url(r'^sources/refresh_state_all', views.refresh_state_all, name='daq/source_refresh_state_all'),
    url(r'^sources/change_state/$', views.source_change_state, name='daq/source_change_state'),

    url(r'^ecc/get_configs/(\d+)$', views.ecc_get_configs, name='daq/ecc_get_configs'),

    url(r'^data_router/$', views.ListDataRoutersView.as_view(), name='daq/data_router_list'),
    url(r'^data_router/add/$', views.AddDataRouterView.as_view(), name='daq/add_data_router'),
    url(r'^data_router/edit/(?P<pk>\d+)$', views.UpdateDataRouterView.as_view(), name='daq/update_data_router'),
    url(r'^data_router/remove/(?P<pk>\d+)$', views.RemoveDataRouterView.as_view(), name='daq/remove_data_router'),

    url(r'^runs/$', views.ListRunMetadataView.as_view(), name='daq/run_list'),
    url(r'^runs/start_run$', views.start_run, name='daq/start_run'),
    url(r'^runs/stop_run$', views.stop_run, name='daq/stop_run'),

    url(r'^experiment_settings/$', views.experiment_settings, name='daq/experiment_settings'),
]
