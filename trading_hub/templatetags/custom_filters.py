from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Template filter to get an item from a dictionary using a key"""
    return dictionary.get(key)

@register.filter(name='multiply')
def multiply(value1, value2):
    """Template filter to multiply two numbers"""
    try:
        return float(value1) * float(value2)
    except (ValueError, TypeError):
        return 0