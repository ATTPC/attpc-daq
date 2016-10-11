from django import template
from ..models import DataSource

register = template.Library()


def get_datasource_attr_from_choices(attr_name, choices):
    value = getattr(DataSource, attr_name, None)

    # Verify that the result is a valid member of the set of choices.
    # This also ensures that we're not just returning any random attribute
    # of the model, but just one member of a set of constants.
    if value not in (key for key, name in choices):
        return None
    else:
        return value


@register.simple_tag
def datasource_state(name):
    return get_datasource_attr_from_choices(name, DataSource.STATE_CHOICES)


@register.simple_tag
def daq_state(name):
    return get_datasource_attr_from_choices(name, DataSource.DAQ_STATE_CHOICES)