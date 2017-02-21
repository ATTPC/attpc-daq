from .models import DataRouter, ECCServer, ConfigId, RunMetadata, Experiment, Observable, Measurement
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


class ObservableSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Observable
        fields = ['url', 'name', 'units', 'comment', 'value_type', 'order']


class MeasurementSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Measurement
        fields = ['observable', 'value']
        depth = 1


class RunMetadataSerializer(serializers.HyperlinkedModelSerializer):
    measurement_set = MeasurementSerializer(
        many=True,
        read_only=True,
    )
    class Meta:
        model = RunMetadata
        fields = ['url', 'run_number', 'title', 'get_run_class_display', 'run_class', 'start_datetime', 'stop_datetime', 'duration_string', 'config_name', 'measurement_set']
        depth = 1


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
