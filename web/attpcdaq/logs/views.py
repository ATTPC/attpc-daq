from django.shortcuts import redirect
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest

from .models import LogEntry

import logging
logger = logging.getLogger(__name__)


class LogEntryListView(LoginRequiredMixin, ListView):
    model = LogEntry
    template_name = 'logs/log_entry_list.html'
    queryset = LogEntry.objects.order_by('-create_time')
    paginate_by = 25

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clear_btn_redirect_target'] = reverse('logs/list')
        return context


class LogEntryListFragmentView(LoginRequiredMixin, ListView):
    model = LogEntry
    template_name = 'logs/log_list_panel_fragment.html'
    queryset = LogEntry.objects.order_by('-create_time')[:10]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clear_btn_redirect_target'] = reverse('daq/status')
        return context


class LogEntryDetailView(LoginRequiredMixin, DetailView):
    model = LogEntry
    template_name = 'logs/log_entry_detail.html'


@login_required
def clear_all_logs(request):
    if request.method == 'POST':
        try:
            next_url = request.POST['next']
        except KeyError:
            logger.error('No "next" url provided in form')
            return HttpResponseBadRequest()

        LogEntry.objects.all().delete()
        return redirect(next_url)

    else:
        logger.error('Request method must be POST, not %s', request.method)
        return HttpResponseNotAllowed(['POST'])
