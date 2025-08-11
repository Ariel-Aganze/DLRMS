from django import template

register = template.Library()

@register.filter
def replace_underscore(value):
    """Replace underscores with spaces in a string"""
    if value:
        return value.replace('_', ' ')
    return value

@register.filter
def format_dispute_type(value):
    """Format dispute type for display"""
    if value:
        return value.replace('_', ' ').title()
    return value