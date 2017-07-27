# -*- coding: utf-8 -*-
from django import template
from django.forms import TimeInput, DateInput
from django.utils import formats
from django.utils.safestring import mark_safe
from markdown import markdown as mkdown
from autoplanner.utils import python_to_str

__author__ = 'Matthieu Gallet'
register = template.Library()


@register.filter
def my_simple_str(x):
    """Seems to be useless, but "no signature found for builtin type <class 'str'>" is raised otherwise"""
    return str(x)


@register.filter
def timedelta(x):
    return mark_safe(python_to_str(x))


@register.filter
def input_time(value):
    if value is None:
        return mark_safe('')
    return mark_safe(formats.localize_input(value, formats.get_format(TimeInput.format_key)[0]))


@register.filter
def int_format(value, fmt=''):
    if value is None:
        return mark_safe('')
    return mark_safe(('%%%sd' % fmt) % value)


@register.filter
def input_date(value):
    if value is None:
        return mark_safe('')
    return mark_safe(formats.localize_input(value, formats.get_format(DateInput.format_key)[0]))


@register.filter
def js_value(value):
    if value is None:
        return mark_safe('null')
    return mark_safe(repr(value))


@register.filter
def markdown(value):
    return mark_safe(mkdown(value))
