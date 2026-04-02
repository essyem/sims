from django import template

register = template.Library()

@register.filter
def contains_arabic(text):
    """Check if text contains Arabic characters"""
    if not text:
        return False
    return any('\u0600' <= char <= '\u06FF' for char in str(text))