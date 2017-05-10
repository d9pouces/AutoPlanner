# -*- coding: utf-8 -*-
import re
from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils import formats
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Task, default_day_start, Category, MaxTaskAffectation
from autoplanner.utils import TimeDeltaField

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


class CategoryNameForm(forms.Form):
    name = forms.CharField(label=_('Name'), max_length=500, min_length=1)


class CategoryBalancingModeForm(forms.Form):
    balancing_mode = forms.ChoiceField(label=_('Balancing mode'), required=False,
                                       choices=((None, _('No balancing')),
                                                (Category.BALANCE_TIME, _('Total task time')),
                                                (Category.BALANCE_NUMBER, _('Total task number'))))


class CategoryBalancingToleranceForm(forms.Form):
    balancing_tolerance = forms.FloatField(label=_('Tolerance while balancing tasks across resources'),
                                           required=False)


class CategoryAutoAffinityForm(forms.Form):
    auto_affinity = forms.FloatField(label=_('Affinity for allocating successive tasks of the same category '
                                             'to the same agent'))


class CategoryAddForm(forms.Form):
    name = forms.CharField(label=_('Name'), max_length=500, min_length=1)
    balancing_mode = forms.ChoiceField(label=_('Balancing mode'), required=False,
                                       choices=((None, _('No balancing')),
                                                (Category.BALANCE_TIME, _('Total task time')),
                                                (Category.BALANCE_NUMBER, _('Total task number'))))
    balancing_tolerance = forms.FloatField(label=_('Tolerance while balancing tasks across resources'),
                                           required=False)
    auto_affinity = forms.FloatField(label=_('Affinity for allocating successive tasks of the same category '
                                             'to the same agent'))


class AgentNameForm(forms.Form):
    name = forms.CharField(label=_('Name'), max_length=500, min_length=1)


class AgentStartTimeForm(forms.Form):
    start_time = forms.DateTimeField(label=_('Arrival time'), required=False)


class AgentEndTimeForm(forms.Form):
    end_time = forms.DateTimeField(label=_('Leaving time'), required=False)


class AgentAddForm(forms.Form):
    name = forms.CharField(label=_('Name'), max_length=500, min_length=1)
    start_time = forms.DateTimeField(label=_('Arrival time'), required=False)


class AgentCategoryPreferencesAffinityForm(forms.Form):
    affinity = forms.FloatField(label=_('Affinity of the agent for the category.'), initial=0.0)


class AgentCategoryPreferencesBalancingOffsetForm(forms.Form):
    balancing_offset = forms.FloatField(label=_('Number of tasks already done'), initial=0.0)


class AgentCategoryPreferencesBalancingOffsetTimeForm(forms.Form):
    balancing_offset = TimeDeltaField(label=_('Time already passed on this category of tasks'), initial='0d')


class AgentCategoryPreferencesBalancingCountForm(forms.Form):
    balancing_count = forms.FloatField(label=_('If a task of this category performed by this agent counts twice, '
                                               'set this number to 2.0.'), initial=1.0, required=False,
                                       help_text=_('Blank if the agent cannot perform tasks of this category'))


class AgentCategoryPreferencesAddForm(forms.Form):
    category = forms.IntegerField()


class MaxTaskAffectationCategoryForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all())


class MaxTaskAffectationModeForm(forms.Form):
    mode = forms.ChoiceField(choices=((MaxTaskAffectation.MINIMUM, _('At least this number of tasks')),
                                      (MaxTaskAffectation.MAXIMUM, _('At most this number of tasks'))),
                             initial=MaxTaskAffectation.MAXIMUM)


class MaxTaskAffectationRangeTimeSliceForm(forms.Form):
    range_time_slice = TimeDeltaField(label=_('Period length (days)'), initial='2d')


class MaxTaskAffectationTaskMaximumCountForm(forms.Form):
    task_maximum_count = forms.IntegerField(label=_('Number of tasks in this range'), initial=1)


class MaxTimeAffectationTaskMaximumTimeForm(forms.Form):
    task_maximum_time = TimeDeltaField(label=_('Number of tasks in this range'), initial='12:00')


class MaxTaskAffectationAddForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    mode = forms.ChoiceField(choices=((MaxTaskAffectation.MINIMUM, _('At least this number of tasks')),
                                      (MaxTaskAffectation.MAXIMUM, _('At most this number of tasks'))),
                             initial=MaxTaskAffectation.MAXIMUM)
    range_time_slice = TimeDeltaField(label=_('Period length (days)'), initial='2d')
    task_maximum_count = forms.IntegerField(label=_('Number of tasks in this range'), initial=1)


class MaxTimeAffectationAddForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.all())
    mode = forms.ChoiceField(choices=((MaxTaskAffectation.MINIMUM, _('At least this number of tasks')),
                                      (MaxTaskAffectation.MAXIMUM, _('At most this number of tasks'))),
                             initial=MaxTaskAffectation.MAXIMUM)
    range_time_slice = TimeDeltaField(label=_('Period length (days)'), initial='2d')
    task_maximum_time = TimeDeltaField(label=_('Number of tasks in this range'), initial='12:00')
