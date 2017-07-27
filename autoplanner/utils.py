# -*- coding: utf-8 -*-
import re

from django.core.validators import RegexValidator
from django.forms import forms
from django.forms.widgets import Input
from django.utils.translation import ugettext as _
import datetime

__author__ = 'Matthieu Gallet'


timedelta_matcher = re.compile(_(r'^\s*((\d+)\s*d\s*|)((\d{1,2})\s*:\s*([0-5]\d)\s*(:\s*([0-5]\d)\s*|)|)$'))


class TimeDeltaInput(Input):
    input_type = 'text'
    template_name = 'django/forms/widgets/text.html'


class TimeDeltaField(forms.Field):
    default_validators = []
    widget = TimeDeltaInput

    def to_python(self, value):
        return str_to_python(value)


def str_to_python(value: str):
    """

    >>> str_to_python('45d 12:34') == datetime.timedelta(days=45, hours=12, minutes=34)
    True
    >>> str_to_python('45d 12:34:56') == datetime.timedelta(days=45, hours=12, minutes=34, seconds=56)
    True
    >>> str_to_python('12:34') == datetime.timedelta(hours=12, minutes=34)
    True
    >>> str_to_python('45d') == datetime.timedelta(days=45)
    True

    :param value:
    :return:
    """
    if not value:
        return None
    matcher = timedelta_matcher.match(value)
    if not matcher:
        raise ValueError()
    groups = matcher.groups()
    result = 0
    if groups[1]:
        result += 86400 * int(groups[1])
    if groups[3]:
        result += 3600 * int(groups[3])
    if groups[4]:
        result += 60 * int(groups[4])
    if groups[5]:
        result += int(groups[6])
    return datetime.timedelta(seconds=result)


def python_to_components(value: datetime.timedelta):
    if value is None:
        return None, None, None
    return value.days, value.seconds // 3600, value.seconds % 3600


def python_to_str(value: datetime.timedelta):
    if value is None:
        return ''
    seconds = int(value.total_seconds())
    days = seconds // 86400
    seconds -= days * 86400
    hours = seconds // 3600
    seconds -= hours * 3600
    minutes = seconds / 60
    seconds -= minutes * 60
    values = {'d': days, 'h': hours, 'm': minutes, 's': seconds}
    if days and seconds:
        return _('%(d)dd %(h)02d:%(m)02d:%(s)02d') % values
    elif days and (minutes, hours) == (0, 0):
        return _('%(d)dd') % values
    elif days:
        return _('%(d)dd %(h)02d:%(m)02d') % values
    elif seconds:
        return _('%(h)02d:%(m)02d:%(s)02d') % values
    return _('%(h)02d:%(m)02d') % values
