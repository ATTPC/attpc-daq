from django.utils.functional import SimpleLazyObject
from django.shortcuts import redirect
from django.urls import reverse
from functools import wraps

from .models import Experiment, ECCServer

import logging
logger = logging.getLogger(__name__)


CURRENT_EXPERIMENT_KEY = 'current_experiment_pk'


def get_current_experiment(request):
    """Returns the experiment listed in the current session."""
    try:
        return Experiment.objects.get(pk=request.session[CURRENT_EXPERIMENT_KEY])
    except KeyError:
        # Handle this below by trying another approach
        pass
    except Experiment.DoesNotExist:
        logger.exception('Invalid experiment pk stored in session.')
        raise

    # Look for a running experiment
    expt = Experiment.objects.filter(eccserver__state__gt=ECCServer.IDLE).distinct()
    if expt.count() == 1:
        request.session[CURRENT_EXPERIMENT_KEY] = expt[0].pk
        return expt[0]
    elif expt.count() == 0:
        return None
    else:
        raise RuntimeError('More than one experiment is running')


def _can_get_experiment(request):
    return (CURRENT_EXPERIMENT_KEY in request.session
            or ECCServer.objects.filter(state__gt=ECCServer.IDLE).exists())


class CurrentExperimentMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.experiment = SimpleLazyObject(lambda: get_current_experiment(request))
        return self.get_response(request)


def needs_experiment(func):
    """Decorator to check if a chosen experiment is set in the current session.
    """
    @wraps(func)
    def wrapped_func(request, *args, **kwargs):
        if _can_get_experiment(request):
            return func(request, *args, **kwargs)
        else:
            return redirect(reverse('daq/choose_experiment'))

    return wrapped_func


class NeedsExperimentMixin:
    def dispatch(self, request, *args, **kwargs):
        if _can_get_experiment(request):
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect(reverse('daq/choose_experiment'))
