from django.contrib import admin

from .models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    model = LogEntry
    list_display = ['create_time', 'logger_name', 'function_name', 'level', 'message']
