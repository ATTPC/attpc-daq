from django.conf.urls import include, url

from . import views

urlpatterns = [
    url(r'^$', views.status, name='daq/status'),
    url(r'^sources/add/$', views.AddDataSourceView.as_view(), name='daq/add_source'),
    url(r'^sources/edit/(?P<pk>\d+)$', views.UpdateDataSourceView.as_view(), name='daq/update_source'),
    url(r'^sources/remove/(?P<pk>\d+)$', views.RemoveDataSourceView.as_view(), name='daq/remove_source'),
    url(r'^ecc/get_state/$', views.get_ecc_server_state, name='daq/get_ecc_server_state'),
    url(r'^state/set_all/(\d)$', views.set_state_all, name='daq/set_state_all'),
]