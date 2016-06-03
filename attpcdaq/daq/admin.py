from django.contrib import admin

from .models import DataSource, ECCServer, DataRouter, ConfigId


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    model = DataSource
    list_display = ['name', 'ecc_server', 'data_router', 'config', 'state_name']


@admin.register(ECCServer)
class ECCServerAdmin(admin.ModelAdmin):
    model = ECCServer
    list_display = ['name', 'ip_address', 'port']


@admin.register(DataRouter)
class DataRouterAdmin(admin.ModelAdmin):
    model = DataRouter
    list_display = ['name', 'ip_address', 'port', 'type']


@admin.register(ConfigId)
class ConfigIdAdmin(admin.ModelAdmin):
    model = ConfigId
    list_display = ['describe', 'prepare', 'configure']