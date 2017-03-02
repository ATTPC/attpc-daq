from django.utils.functional import SimpleLazyObject
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps

from .models import Experiment

import logging
logger = logging.getLogger(__name__)


def get_current_experiment():
    """Returns the experiment listed in the current session."""
    try:
        return Experiment.objects.get(is_active=True)
    except Experiment.DoesNotExist:
        return None


def _can_get_experiment():
    return Experiment.objects.filter(is_active=True).exists()


class CurrentExperimentMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.experiment = SimpleLazyObject(get_current_experiment)
        return self.get_response(request)


def needs_experiment(func):
    """Decorator to check if a chosen experiment is set in the current session.
    """
    @wraps(func)
    def wrapped_func(request, *args, **kwargs):
        if _can_get_experiment():
            return func(request, *args, **kwargs)
        else:
            return redirect(reverse('daq/choose_experiment'))

    return wrapped_func


class NeedsExperimentMixin:
    def dispatch(self, request, *args, **kwargs):
        if _can_get_experiment():
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect(reverse('daq/choose_experiment'))
