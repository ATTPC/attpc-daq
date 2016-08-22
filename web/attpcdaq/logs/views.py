from django.shortcuts import render
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from .models import LogEntry


class LogEntryListView(LoginRequiredMixin, ListView):
    model = LogEntry
    template_name = 'logs/log_entry_list.html'
    queryset = LogEntry.objects.order_by('-create_time')


class LogEntryListFragmentView(LoginRequiredMixin, ListView):
    model = LogEntry
    template_name = 'logs/log_list_panel_fragment.html'
    queryset = LogEntry.objects.order_by('-create_time')[:10]


class LogEntryDetailView(LoginRequiredMixin, DetailView):
    model = LogEntry
    template_name = 'logs/log_entry_detail.html'
