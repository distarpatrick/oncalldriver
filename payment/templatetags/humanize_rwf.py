from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rwf(value):
    """Format an amount with thousands separators: 1500000 -> 1,500,000."""
    try:
        return f"{int(Decimal(str(value).replace(',', ''))):,}"
    except (InvalidOperation, ValueError, TypeError):
        return value
