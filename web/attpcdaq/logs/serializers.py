from rest_framework import serializers

from .models import LogEntry


class LogEntrySerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = LogEntry
        fields = ['pk', 'logger_name', 'create_time', 'get_level_display', 'message']
