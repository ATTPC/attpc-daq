from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.LogEntryListView.as_view(), name='logs/list'),
    url(r'^recent_panel/', views.LogEntryListFragmentView.as_view(), name='logs/recent_panel'),
    url(r'^details/(?P<pk>\d+)/', views.LogEntryDetailView.as_view(), name='logs/details'),
    url(r'^clear/', views.clear_all_logs, name='logs/clear'),
]
