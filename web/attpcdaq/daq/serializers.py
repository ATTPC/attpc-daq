from .models import DataRouter, ECCServer, ConfigId, RunMetadata, Experiment

from rest_framework import serializers
from django.core.urlresolvers import reverse


class DataRouterSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = DataRouter
        fields = '__all__'


class ECCServerSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ECCServer
        fields = ['name', 'ip_address', 'port', 'get_state_display', 'is_transitioning', 'is_online', 'selected_config', 'url']


class ConfigIdSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ConfigId
        fields = '__all__'


class RunMetadataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RunMetadata
        fields = '__all__'


class ExperimentSerializer(serializers.HyperlinkedModelSerializer):
    latest_run = RunMetadataSerializer()
    class Meta:
        model = Experiment
        fields = ['name', 'latest_run', 'is_running', 'target_run_duration']
