from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register('log_entries', views.LogEntryViewSet)

urlpatterns = [
    url(r'^$', views.LogEntryListView.as_view(), name='logs/list'),
    url(r'^recent_panel/', views.LogEntryListFragmentView.as_view(), name='logs/recent_panel'),
    url(r'^details/(?P<pk>\d+)/', views.LogEntryDetailView.as_view(), name='logs/details'),
    url(r'^clear/', views.clear_all_logs, name='logs/clear'),

    url(r'api/', include(router.urls)),
    url(r'api/api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]
