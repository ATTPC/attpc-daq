"""View helper functions

The functions in this module are helpers to get information for the main views. These
could be shared between multiple views.

"""

from ..models import ECCServer, DataRouter

import logging
logger = logging.getLogger(__name__)


def calculate_overall_state(request):
    """Find the overall state of the system.

    Parameters
    ----------
    request : django.http.request.HttpRequest
        The request object.

    Returns
    -------
    overall_state : int or None
        The overall state of the system. Returns ``None`` if the state is mixed.
    overall_state_name : str
        The name of the system state. The value 'Mixed' is returned if the system is not in a
        consistent state.

    """
    ecc_server_list = ECCServer.objects.filter(experiment=request.experiment)
    if len(set(s.state for s in ecc_server_list)) == 1:
        # All states are the same
        overall_state = ecc_server_list.first().state
        overall_state_name = ecc_server_list.first().get_state_display()
    else:
        overall_state = None
        overall_state_name = 'Mixed'

    return overall_state, overall_state_name


def get_ecc_server_statuses(request):
    """Gets some information about the ECC servers.

    This produces a dictionary with the following key-value pairs:

    'success'
        Whether the request succeeded.
    'error_message'
        An error message, if applicable.
    'pk'
        The integer primary key of the ECC server in the database.
    'state'
        The current (integer) state of the ECC server, as enumerated in the constants attached to that class.
    'state_name'
        The name of the current state of the ECC server.
    'transitioning'
        Whether the ECC server is transitioning between states.

    Returns
    -------
    dict
        A dictionary with the above keys.

    """
    ecc_server_status_list = []
    for ecc_server in ECCServer.objects.filter(experiment=request.experiment):
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


def get_data_router_statuses(request):
    """Gets some information about the data routers.

    This produces a dictionary with the following key-value pairs:

    'success'
        Whether the request succeeded.
    'pk'
        The integer primary key of the data router in the database.
    'is_online'
        Whether the router is available.
    'is_clean'
        Whether the staging directory is clean.

    Returns
    -------
    dict
        A dictionary of the values above.

    """
    data_router_status_list = []
    for router in DataRouter.objects.filter(experiment=request.experiment):
        router_res = {
            'success': True,
            'pk': router.pk,
            'is_online': router.is_online,
            'is_clean': router.staging_directory_is_clean,
        }
        data_router_status_list.append(router_res)

    return data_router_status_list


def get_status(request):
    """Returns some information about the system's status.

    This generates a dictionary containing the following key-value pairs:

    'overall_state'
        The overall state of the system. If all of the data sources have the same state, this should
        be the numerical ID of a state. If the sources have different states, it should be -1.
    'overall_state_name'
        The name of the overall state of the system. Either a state name or "Mixed" if the state
        is inconsistent.
    'run_number'
        The current run number.
    'run_title'
        The title of the current run.
    'run_class'
        The type of the current run.
    'start_time'
        The date and time when the current run started.
    'run_duration'
        The duration of the current run. This is with respect to the current time if the run
        has not ended.
    'ecc_server_status_list'
        Status of each ECC server. See :func:`get_ecc_server_statuses` for details.
    'data_router_status_list'
        Status of each data router. See :func:`get_data_router_statuses` for details.

    This is helpful when generating JSON responses to update the main page periodically.

    Parameters
    ----------
    request : HttpRequest
        The request object. This must be included so we can get the name of the current user when fetching the
        :class:`~attpcdaq.daq.models.Experiment` object.

    Returns
    -------
    dict
        A dictionary containing the information above.

    """
    ecc_server_status_list = get_ecc_server_statuses(request)
    data_router_status_list = get_data_router_statuses(request)
    overall_state, overall_state_name = calculate_overall_state(request)

    current_run = request.experiment.latest_run
    if current_run is not None:
        run_number = current_run.run_number
        start_time = current_run.start_datetime.strftime('%b %d %Y, %H:%M:%S')
        duration_str = current_run.duration_string
        run_title = current_run.title
        run_class = current_run.get_run_class_display()
    else:
        run_number = None
        start_time = None
        duration_str = None
        run_title = None
        run_class = None

    output = {
        'overall_state': overall_state,
        'overall_state_name': overall_state_name,
        'ecc_server_status_list': ecc_server_status_list,
        'data_router_status_list': data_router_status_list,
        'run_number': run_number,
        'start_time': start_time,
        'run_duration': duration_str,
        'run_title': run_title,
        'run_class': run_class,
    }

    return output
