from django import template

from manager.order_status import order_status_bucket

register = template.Library()


@register.filter
def status_bucket(status):
    return order_status_bucket(status)
