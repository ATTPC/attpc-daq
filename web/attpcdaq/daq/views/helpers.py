"""View helper functions

The functions in this module are helpers to get information for the main views. These
could be shared between multiple views.

"""

from ..models import ECCServer

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
