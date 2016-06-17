from django import template
import re

register = template.Library()


@register.simple_tag
def active(request, pattern):
    # http://stackoverflow.com/a/477719/3820658
    if re.search(pattern, request.path):
        return 'active'
    else:
        return ''
