from django.conf.urls import url
import django.contrib.auth.views as auth_views

urlpatterns = [
    url(r'^login/', auth_views.login, {'template_name': 'accounts/login.html'}, name='accounts/login'),
    url(r'^logout/', auth_views.logout, {'template_name': 'accounts/logout.html'}, name='accounts/logout'),
]
