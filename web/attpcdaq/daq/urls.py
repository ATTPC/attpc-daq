from django.conf.urls import include, url
from django.views.generic import RedirectView, TemplateView
from rest_framework import routers

from . import views

router = routers.DefaultRouter()
router.register(r'data_routers', views.DataRouterViewSet)
router.register(r'ecc_servers', views.ECCServerViewSet)
router.register(r'configids', views.ConfigIdViewSet)
router.register(r'runmetadata', views.RunMetadataViewSet, base_name='runmetadata')
router.register(r'experiment', views.ExperimentViewSet, base_name='experiment')

urlpatterns = [
    url(r'^$', RedirectView.as_view(pattern_name='daq/status')),
    url(r'^status/$', views.status, name='daq/status'),
    url(r'app/.*$', TemplateView.as_view(template_name='daq/app.html'), name='daq/app'),

    url(r'^sources/$', views.ListDataSourcesView.as_view(), name='daq/data_source_list'),
    url(r'^sources/add/$', views.AddDataSourceView.as_view(), name='daq/add_source'),
    url(r'^sources/edit/(?P<pk>\d+)$', views.UpdateDataSourceView.as_view(), name='daq/update_source'),
    url(r'^sources/remove/(?P<pk>\d+)$', views.RemoveDataSourceView.as_view(), name='daq/remove_source'),
    url(r'^sources/choose_config/(\d+)$', views.choose_config, name='daq/choose_config'),

    url(r'^ecc_servers/$', views.ListECCServersView.as_view(), name='daq/ecc_server_list'),
    url(r'^ecc_servers/add/$', views.AddECCServerView.as_view(), name='daq/add_ecc_server'),
    url(r'^ecc_servers/edit/(?P<pk>\d+)$', views.UpdateECCServerView.as_view(), name='daq/update_ecc_server'),
    url(r'^ecc_servers/remove/(?P<pk>\d+)$', views.RemoveECCServerView.as_view(), name='daq/remove_ecc_server'),

    url(r'^data_routers/$', views.ListDataRoutersView.as_view(), name='daq/data_router_list'),
    url(r'^data_routers/add/$', views.AddDataRouterView.as_view(), name='daq/add_data_router'),
    url(r'^data_routers/edit/(?P<pk>\d+)$', views.UpdateDataRouterView.as_view(), name='daq/update_data_router'),
    url(r'^data_routers/remove/(?P<pk>\d+)$', views.RemoveDataRouterView.as_view(), name='daq/remove_data_router'),

    url(r'^sources/download/$', views.download_datasource_list, name='daq/download_datasource_list'),
    url(r'^sources/upload/$', views.upload_datasource_list, name='daq/upload_datasource_list'),

    url(r'^runs/$', views.ListRunMetadataView.as_view(), name='daq/run_list'),
    url(r'^runs/edit/(?P<pk>\d+)$', views.UpdateRunMetadataView.as_view(), name='daq/update_run_metadata'),
    url(r'^runs/edit/latest$', views.UpdateLatestRunMetadataView.as_view(), name='daq/update_latest_run'),
    url(r'^runs/download$', views.download_run_metadata, name='daq/download_run_metadata'),

    url(r'^observables/$', views.ListObservablesView.as_view(), name='daq/observables_list'),
    url(r'^observables/add/$', views.AddObservableView.as_view(), name='daq/add_observable'),
    url(r'^observables/edit/(?P<pk>\d+)$', views.UpdateObservableView.as_view(), name='daq/update_observable'),
    url(r'^observables/remove/(?P<pk>\d+)$', views.RemoveObservableView.as_view(), name='daq/remove_observable'),
    url(r'^observables/set_ordering$', views.set_observable_ordering, name='daq/set_observable_ordering'),

    url(r'^measurements/$', views.measurement_chart, name='daq/measurement_chart'),

    url(r'^experiment_settings/$', views.experiment_settings, name='daq/experiment_settings'),

    url(r'^status/(?P<program>ecc|data_router)_log/(?P<pk>\d+)/$', views.show_log_page, name='daq/show_log'),

    url(r'^easy_setup/$', views.easy_setup_page, name='daq/easy_setup'),

    url(r'api/', include(router.urls)),
    url(r'api/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
