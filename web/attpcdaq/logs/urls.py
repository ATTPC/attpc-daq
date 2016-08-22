from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.LogEntryListView.as_view(), name='logs/list'),
    url(r'^recent_panel', views.LogEntryListFragmentView.as_view(), name='logs/recent_panel'),
]
