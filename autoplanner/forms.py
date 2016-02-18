# -*- coding: utf-8 -*-
from django import forms
from autoplanner.models import Task, default_day_start
from django.utils.translation import ugettext_lazy as _

__author__ = 'Matthieu Gallet'


class MultiplyTaskForm(forms.Form):
    source_task = forms.ModelChoiceField(queryset=Task.objects.all(),
                                         widget=forms.HiddenInput())
    until = forms.DateTimeField(label=_('Duplicate this task until'), initial=default_day_start)
    every = forms.IntegerField(label=_('Days between successive task starts'), min_value=1)