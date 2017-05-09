# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

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
