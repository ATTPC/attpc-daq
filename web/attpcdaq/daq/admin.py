from django.contrib import admin

from .models import DataSource, DataRouter, ConfigId, RunMetadata, Experiment


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    model = DataSource
    list_display = ['name', 'ecc_ip_address', 'ecc_port', 'data_router', 'selected_config', 'get_state_display']


@admin.register(DataRouter)
class DataRouterAdmin(admin.ModelAdmin):
    model = DataRouter
    list_display = ['name', 'ip_address', 'port', 'type']


@admin.register(ConfigId)
class ConfigIdAdmin(admin.ModelAdmin):
    model = ConfigId
    list_display = ['__str__', 'describe', 'prepare', 'configure']


@admin.register(RunMetadata)
class RunMetadataAdmin(admin.ModelAdmin):
    model = RunMetadata
    list_display = ['run_number', 'start_datetime', 'stop_datetime']


@admin.register(Experiment)
class ExperimentAdmin(admin.ModelAdmin):
    model = Experiment
    list_display = ['name', 'user']
