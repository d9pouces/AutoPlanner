# -*- coding: utf-8 -*-
from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Task, default_day_start


__author__ = 'Matthieu Gallet'


class MultiplyTaskForm(forms.Form):
    source_task = forms.ModelChoiceField(queryset=Task.objects.all(),
                                         widget=forms.HiddenInput())
    until = forms.DateTimeField(label=_('Duplicate this task until'), initial=default_day_start,
                                widget=AdminDateWidget()
                                )
    every = forms.IntegerField(label=_('Days between successive task starts'), min_value=1, initial=7)