from django import template

register = template.Library()


@register.filter(name='split')
def split_filter(value, arg):
    """Split a string by a separator. Usage: {{ "a,b,c"|split:',' }}"""
    return value.split(arg)


@register.filter(name='get_item')
def get_item(dictionary, key):
    """Get a dict item by key. Usage: {{ mydict|get_item:key }}"""
    return dictionary.get(key)
