from django import template

register = template.Library()

@register.filter
def startswith(value, prefix):
    """Check if a string starts with the given prefix."""
    return str(value).startswith(prefix)