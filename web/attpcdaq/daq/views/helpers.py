"""View helper functions

The functions in this module are helpers to get information for the main views. These
could be shared between multiple views.

"""

from django.shortcuts import get_object_or_404
from django.http import JsonResponse

from ..models import DataSource, ECCServer, DataRouter, Experiment

import logging
logger = logging.getLogger(__name__)


def calculate_overall_state():
    """Find the overall state of the system.

    Parameters
    ----------
    ecc_server_list : QuerySet
        A set of DataSource objects.

    Returns
    -------
    overall_state : int or None
        The overall state of the system. Returns ``None`` if the state is mixed.
    overall_state_name : str
        The name of the system state. The value 'Mixed' is returned if the system is not in a
        consistent state.

    """
    ecc_server_list = ECCServer.objects.all()
    if len(set(s.state for s in ecc_server_list)) == 1:
        # All states are the same
        overall_state = ecc_server_list.first().state
        overall_state_name = ecc_server_list.first().get_state_display()
    else:
        overall_state = None
        overall_state_name = 'Mixed'

    return overall_state, overall_state_name


def get_ecc_server_statuses():
    ecc_server_status_list = []
    for ecc_server in ECCServer.objects.all():
        ecc_res = {
            'success': True,
            'pk': ecc_server.pk,
            'error_message': "",
            'state': ecc_server.state,
            'state_name': ecc_server.get_state_display(),
            'transitioning': ecc_server.is_transitioning,
        }
        ecc_server_status_list.append(ecc_res)

    return ecc_server_status_list


def get_data_router_statuses():
    data_router_status_list = []
    for router in DataRouter.objects.all():
        router_res = {
            'success': True,
            'pk': router.pk,
            'is_online': router.is_online,
            'is_clean': router.staging_directory_is_clean,
        }
        data_router_status_list.append(router_res)

    return data_router_status_list

def get_status(request):
    ecc_server_status_list = get_ecc_server_statuses()
    data_router_status_list = get_data_router_statuses()
    overall_state, overall_state_name = calculate_overall_state()

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
        'ecc_server_status_list': ecc_server_status_list,
        'data_router_status_list': data_router_status_list,
        'run_number': run_number,
        'start_time': start_time,
        'run_duration': duration_str,
    }

    return output
