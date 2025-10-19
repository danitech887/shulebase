from django import template
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
