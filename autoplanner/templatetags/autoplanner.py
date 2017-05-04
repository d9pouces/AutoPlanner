# -*- coding: utf-8 -*-
from django import template

__author__ = 'Matthieu Gallet'
register = template.Library()


@register.filter
def my_simple_str(x):
    """Seems to be useless, but "no signature found for builtin type <class 'str'>" is raised otherwise"""
    return str(x)
