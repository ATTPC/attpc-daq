from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from ..models import DataSource, Experiment

import logging
logger = logging.getLogger(__name__)


def make_status_response(success=True, pk=None, error_message=None, state=None,
                         state_name=None, transitioning=False):
    """A helper function to generate a JSON response for the main status page.

    Parameters
    ----------
    success : bool, optional
        Did the request succeed?
    pk : int, optional
        The primary key of the object associated with the request.
    error_message : str, optional
        An error message to display, if applicable.
    state : int, optional
        The integer identifying the current state of the object with primary key ``pk``, if applicable.
    state_name : str, optional
        The display name of the state.
    transitioning : bool, optional
        Is the system undergoing a transition?

    Returns
    -------
    JsonResponse
        Contains a JSON array of the above keys.

    """
    output = {
        'success': success,
        'pk': pk,
        'error_message': error_message,
        'state': state,
        'state_name': state_name,
        'transitioning': transitioning,
    }
    return JsonResponse(output)


def make_runcontrol_response(success, run_number=None, start_time=None, error_message=None):
    output = {
        'success': success,
        'run_number': run_number,
        'start_time': start_time,
        'error_message': error_message,
    }
    return JsonResponse(output)


def calculate_overall_state(source_list):
    """Find the overall state of the system.

    Parameters
    ----------
    source_list : QuerySet
        A set of DataSource objects.

    Returns
    -------
    overall_state : int or None
        The overall state of the system. Returns ``None`` if the state is mixed.
    overall_state_name : str
        The name of the system state. The value 'Mixed' is returned if the system is not in a
        consistent state.

    """
    if len(set(s.state for s in source_list)) == 1:
        # All states are the same
        overall_state = source_list.first().state
        overall_state_name = source_list.first().get_state_display()
    else:
        overall_state = None
        overall_state_name = 'Mixed'

    return overall_state, overall_state_name


def get_status(request):
    results = []

    for source in DataSource.objects.all():
        source_res = {
            'success': True,
            'pk': source.pk,
            'error_message': "",
            'state': source.state,
            'state_name': source.get_state_display(),
            'transitioning': source.is_transitioning,
            'daq_state': source.daq_state,
            'daq_state_string': source.get_daq_state_display(),
        }

        results.append(source_res)

    overall_state, overall_state_name = calculate_overall_state(DataSource.objects.all())

    experiment = get_object_or_404(Experiment, user=request.user)
    current_run = experiment.latest_run
    if current_run is not None:
        run_number = current_run.run_number
        start_time = current_run.start_datetime.strftime('%b %d %Y, %H:%M:%S')
        duration_str = current_run.duration_string
    else:
        run_number = None
        start_time = None
        duration_str = None

    output = {
        'overall_state': overall_state,
        'overall_state_name': overall_state_name,
        'individual_results': results,
        'run_number': run_number,
        'start_time': start_time,
        'run_duration': duration_str,
    }

    return output