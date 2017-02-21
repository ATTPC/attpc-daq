from .models import DataRouter, ECCServer, ConfigId, RunMetadata, Experiment
from django.contrib.auth.models import User

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
        depth = 1


class ConfigIdSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = ConfigId
        fields = '__all__'


class RunMetadataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = RunMetadata
        fields = ['url', 'run_number', 'title', 'get_run_class_display', 'run_class', 'start_datetime', 'stop_datetime', 'duration_string', 'config_name']


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['username']


class ExperimentSerializer(serializers.HyperlinkedModelSerializer):
    latest_run = RunMetadataSerializer()
    user = UserSerializer()
    class Meta:
        model = Experiment
        fields = ['name', 'latest_run', 'is_running', 'target_run_duration', 'user']
        depth = 1
