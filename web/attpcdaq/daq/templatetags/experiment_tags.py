from django import template
from ..views.helpers import get_current_experiment

register = template.Library()

@register.simple_tag
def current_experiment_name(request):
    """Returns the name of the selected experiment."""
    expt = get_current_experiment(request)
    return str(expt.name)
