# -*- coding: utf-8 -*-
from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Task, default_day_start, Organization

__author__ = 'Matthieu Gallet'


class MultiplyTaskForm(forms.Form):
    source_task = forms.ModelChoiceField(queryset=Task.objects.all(),
                                         widget=forms.HiddenInput())
    until = forms.DateTimeField(label=_('Duplicate this task until'), initial=default_day_start,
                                widget=AdminDateWidget()
                                )
    every = forms.IntegerField(label=_('Days between successive task starts'), min_value=1, initial=7)


class OrganizationDescriptionForm(forms.Form):
    description = forms.CharField(required=False)


class OrganizationAccessTokenForm(forms.Form):
    access_token = forms.CharField(required=False, min_length=1, max_length=300,
                                   validators=[RegexValidator(r'^[a-zA-Z0-9]{1,300}$')])


class OrganizationMaxComputeTimeForm(forms.Form):
    max_compute_time = forms.IntegerField(required=False, min_value=0)
