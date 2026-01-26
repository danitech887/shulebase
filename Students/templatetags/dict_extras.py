from django import template
register = template.Library()
from django.db.models import QuerySet

from django import template
import urllib.parse

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary and key in dictionary:
        return dictionary.get(key)
    return ''


@register.filter
def zip_lists(a, b):
    return zip(a, b)

@register.filter
def map_attr(objects, attr):
    return [getattr(obj, attr, '') for obj in objects]

@register.filter
def mul(value, arg):
    """Multiplies the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''
    
@register.filter
def dictsum(queryset, field_name, value):
    """Counts the number of items in a queryset where field_name equals value."""
    if isinstance(queryset, QuerySet):
        return queryset.filter(**{field_name: value}).count()

    # Fallback for plain lists/data structures if needed
    count = 0
    for item in queryset:
        if getattr(item, field_name, None) == value:
            count += 1 
    return count

@register.filter
def divisibleby(numerator, denominator):
    """Simple division filter for percentage calculation."""
    try:
        return numerator / denominator
    except (ZeroDivisionError, TypeError):
        return 0



# Students/templatetags/whatsapp_tags.py


@register.filter
def whatsapp_url(student):
    message = f"Hi {student.parent_name}, your child's results are ready."
    phone = student.parent_phone
    # Simple formatting
    clean_phone = '254' + phone[1:] if phone.startswith('0') else phone
    return f"https://wa.me/{clean_phone}?text={urllib.parse.quote(message)}"
