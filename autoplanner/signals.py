# -*- coding: utf-8 -*-
import calendar
import csv
import datetime
import json
import re

import markdown
from django import forms
from django.utils.timezone import utc
from django.utils.translation import ugettext as _
from djangofloor.decorators import signal, is_authenticated, everyone, SerializedForm, Choice
from djangofloor.signals.bootstrap3 import notify, NOTIFICATION, DANGER, modal_show, INFO, modal_hide
from djangofloor.signals.html import render_to_client, add_attribute, remove_class, add_class, remove, before, focus, \
    content, replace_with
from djangofloor.wsgi.window_info import render_to_string

from autoplanner.forms import OrganizationDescriptionForm, OrganizationAccessTokenForm, OrganizationMaxComputeTimeForm, \
    CategoryNameForm, CategoryBalancingModeForm, CategoryAutoAffinityForm, CategoryAddForm, AgentAddForm, AgentNameForm, \
    AgentStartTimeForm, AgentEndTimeForm, \
    AgentCategoryPreferencesAffinityForm, AgentCategoryPreferencesAddForm, AgentCategoryPreferencesBalancingOffsetForm, \
    AgentCategoryPreferencesBalancingCountForm, MaxTaskAffectationAddForm, MaxTaskAffectationModeForm, \
    MaxTaskAffectationCategoryForm, MaxTaskAffectationTaskMaximumCountForm, MaxTaskAffectationRangeTimeSliceForm, \
    AgentCategoryPreferencesBalancingOffsetTimeForm, MaxTimeAffectationTaskMaximumTimeForm, MaxTimeAffectationAddForm, \
    CategoryBalancingToleranceTimeForm, CategoryBalancingToleranceNumberForm, AgentStartDateForm, AgentEndDateForm, \
    TaskNameForm, TaskStartTimeForm, TaskEndTimeForm, TaskStartDateForm, TaskEndDateForm, TaskAgentForm, \
    TaskCategoriesForm, TaskAddForm, TaskMultiplyForm, TaskMultipleUpdateForm, TaskImportForm, TaskMultipleRemoveForm
from autoplanner.models import Organization, default_token, Category, Agent, AgentCategoryPreferences, \
    MaxTaskAffectation, MaxTimeTaskAffectation, Task, ScheduleRun, API_KEY_VARIABLE
from autoplanner.schedule import Scheduler
from autoplanner.utils import python_to_components
from autoplanner.tasks import compute_schedule, kill_schedule, apply_schedule

__author__ = 'Matthieu Gallet'


def int_or_none(value):
    if value is None or value == '':
        return value
    return int(value)


@signal(is_allowed_to=everyone, path='autoplanner.change_tab', queue='fast')
def change_tab(window_info, organization_pk: int, tab_name: str):
    obj = Organization.query(window_info).filter(pk=organization_pk).first()
    fn = {'general': change_tab_general, 'categories': change_tab_categories,
          'agents': change_tab_agents, 'balancing': change_tab_balancing, 'tasks': change_tab_tasks,
          'schedules': change_tab_schedules, 'schedule': change_tab_schedule
          }.get(tab_name)
    if fn:
        fn(window_info, obj)


def change_tab_general(window_info, organization):
    context = {'organization': organization, }
    render_to_client(window_info, 'autoplanner/tabs/general.html', context, '#general')


def change_tab_categories(window_info, organization):
    queryset = Category.objects.filter(organization=organization).order_by('name')
    # noinspection PyProtectedMember
    balancing_modes = Category._meta.get_field('balancing_mode').choices
    context = {'organization': organization, 'categories': queryset,
               'balancing_modes': balancing_modes, 'new_category': Category()}
    render_to_client(window_info, 'autoplanner/tabs/categories.html', context, '#categories')


def change_tab_agents(window_info, organization):
    queryset = Agent.objects.filter(organization=organization).order_by('name')
    context = {'organization': organization, 'agents': queryset, 'new_agent': Agent()}
    render_to_client(window_info, 'autoplanner/tabs/agents.html', context, '#agents')


def change_tab_balancing(window_info, organization):
    task_queryset = MaxTaskAffectation.objects.filter(organization=organization)
    time_queryset = MaxTimeTaskAffectation.objects.filter(organization=organization)
    categories_queryset = list(Category.objects.filter(organization=organization).order_by('name'))
    context = {'organization': organization, 'max_task_affectations': task_queryset,
               'max_time_affectations': time_queryset, 'categories': categories_queryset,
               'new_max_task_affectation': MaxTaskAffectation(),
               'new_max_time_affectation': MaxTimeTaskAffectation()}
    render_to_client(window_info, 'autoplanner/tabs/balancing.html', context, '#balancing')


def change_tab_tasks(window_info, organization, order_by: Choice(Task.orders) = 'start_time',
                     agent_id: int = None, category_id: int = None, pattern: str = ''):
    task_queryset = Task.objects.filter(organization=organization).select_related('agent', 'task_serie') \
        .order_by(order_by)
    if agent_id:
        task_queryset = task_queryset.filter(agent__id=agent_id)
    if category_id:
        task_queryset = task_queryset.filter(categories__id=category_id)
    if pattern:
        task_queryset = task_queryset.filter(name__icontains=pattern)
    task_queryset = list(task_queryset)
    categories = list(Category.objects.filter(organization=organization).order_by('name'))
    agents = list(Agent.objects.filter(organization=organization).order_by('name'))
    affected_categories = {}
    for task_category in Task.categories.through.objects.filter(category__id__in=[x.id for x in categories]):
        affected_categories.setdefault(task_category.task_id, set()).add(task_category.category_id)
    tasks_categories = [(task, affected_categories.get(task.id)) for task in task_queryset]
    context = {'organization': organization, 'tasks_categories': tasks_categories, 'categories': categories,
               'agents': agents, 'agent_id': agent_id, 'order_by': order_by, 'category_id': category_id,
               'new_task': Task(), 'empty_set': set(), 'pattern': pattern}
    render_to_client(window_info, 'autoplanner/tabs/tasks.html', context, '#tasks')
    for task, task_categories in tasks_categories:
        context['obj'] = task
        context['obj_categories'] = task_categories
        content_str = render_to_string('autoplanner/include/task.html', context=context, window_info=window_info)
        before(window_info, '#row_task_None', content_str)


def change_tab_schedules(window_info, organization):
    schedule_queryset = ScheduleRun.objects.filter(organization=organization).order_by('-celery_start')
    context = {'organization': organization, 'schedules': schedule_queryset}
    render_to_client(window_info, 'autoplanner/tabs/schedules.html', context, '#schedules')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_description')
def set_description(window_info, organization_pk: int, value: SerializedForm(OrganizationDescriptionForm)):
    if value and value.is_valid():
        description = value.cleaned_data['description']
        Organization.query(window_info).filter(pk=organization_pk).update(description=description)
        add_attribute(window_info, '#check_description', 'class', 'fa fa-check')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_access_token')
def set_access_token(window_info, organization_pk: int, value: SerializedForm(OrganizationAccessTokenForm)):
    if value and value.is_valid():
        access_token = value.cleaned_data['access_token']
        Organization.query(window_info).filter(pk=organization_pk).update(access_token=access_token)
        add_attribute(window_info, '#check_access_token', 'class', 'fa fa-check')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.new_access_token')
def new_access_token(window_info, organization_pk: int):
    access_token = default_token()
    Organization.query(window_info).filter(pk=organization_pk).update(access_token=access_token)
    add_attribute(window_info, '#check_access_token', 'class', 'fa fa-check')
    add_attribute(window_info, '#id_access_token', 'value', access_token)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_compute_time')
def set_max_compute_time(window_info, organization_pk: int, value: SerializedForm(OrganizationMaxComputeTimeForm)):
    if value and value.is_valid():
        max_compute_time = value.cleaned_data['max_compute_time']
        Organization.query(window_info).filter(pk=organization_pk).update(max_compute_time=max_compute_time)
        add_attribute(window_info, '#check_max_compute_time', 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_compute_time', 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_category_name')
def set_category_name(window_info, organization_pk: int, category_pk: int, value: SerializedForm(CategoryNameForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        name = value.cleaned_data['name']
        Category.objects.filter(organization__id=organization_pk, pk=category_pk).update(name=name)
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_category_balancing_mode')
def set_category_balancing_mode(window_info, organization_pk: int,
                                value: SerializedForm(CategoryBalancingModeForm), category_pk: int = None):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_mode = value.cleaned_data['balancing_mode']
        if category_pk:
            Category.objects.filter(organization__id=organization_pk, pk=category_pk) \
                .update(balancing_mode=balancing_mode or None)
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-check')
        if balancing_mode == Category.BALANCE_TIME:
            add_class(window_info, '#id_balancing_tolerance_%s_number' % category_pk, 'hidden')
            remove_class(window_info, '#id_balancing_tolerance_%s_time' % category_pk, 'hidden')
            add_class(window_info, '#legend_balancing_tolerance_%s_number' % category_pk, 'hidden')
            remove_class(window_info, '#legend_balancing_tolerance_%s_time' % category_pk, 'hidden')
        elif balancing_mode == Category.BALANCE_NUMBER:
            remove_class(window_info, '#id_balancing_tolerance_%s_number' % category_pk, 'hidden')
            add_class(window_info, '#id_balancing_tolerance_%s_time' % category_pk, 'hidden')
            remove_class(window_info, '#legend_balancing_tolerance_%s_number' % category_pk, 'hidden')
            add_class(window_info, '#legend_balancing_tolerance_%s_time' % category_pk, 'hidden')
        else:
            add_class(window_info, '#id_balancing_tolerance_%s_number' % category_pk, 'hidden')
            add_class(window_info, '#id_balancing_tolerance_%s_time' % category_pk, 'hidden')
            add_class(window_info, '#legend_balancing_tolerance_%s_number' % category_pk, 'hidden')
            add_class(window_info, '#legend_balancing_tolerance_%s_time' % category_pk, 'hidden')
    elif value:
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_category_balancing_tolerance_time')
def set_category_balancing_tolerance_time(window_info, organization_pk: int, category_pk: int,
                                          value: SerializedForm(CategoryBalancingToleranceTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_tolerance = value.cleaned_data['balancing_tolerance']
        Category.objects.filter(organization__id=organization_pk, pk=category_pk).update(
            balancing_tolerance=balancing_tolerance.total_seconds() / 2.0)
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_category_balancing_tolerance_number')
def set_category_balancing_tolerance_number(window_info, organization_pk: int, category_pk: int,
                                            value: SerializedForm(CategoryBalancingToleranceNumberForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_tolerance = value.cleaned_data['balancing_tolerance']
        Category.objects.filter(organization__id=organization_pk, pk=category_pk).update(
            balancing_tolerance=balancing_tolerance / 2.0)
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_category_auto_affinity')
def set_category_auto_affinity(window_info, organization_pk: int, category_pk: int,
                               value: SerializedForm(CategoryAutoAffinityForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        auto_affinity = value.cleaned_data['auto_affinity']
        Category.objects.filter(organization__id=organization_pk, pk=category_pk).update(
            auto_affinity=auto_affinity)
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_category')
def add_category(window_info, organization_pk: int, value: SerializedForm(CategoryAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    can_update = organization is not None
    if can_update and value and value.is_valid():
        # noinspection PyProtectedMember
        balancing_modes = Category._meta.get_field('balancing_mode').choices
        category = Category(organization_id=organization_pk, name=value.cleaned_data['name'],
                            balancing_mode=value.cleaned_data['balancing_mode'],
                            balancing_tolerance=value.cleaned_data['balancing_tolerance'],
                            auto_affinity=value.cleaned_data['auto_affinity'])
        category.save()
        context = {'organization': organization, 'balancing_modes': balancing_modes, 'obj': category}
        content_str = render_to_string('autoplanner/include/category.html', context=context, window_info=window_info)
        before(window_info, '#row_category_None', content_str)
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_category_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_category')
def remove_category(window_info, organization_pk: int, category_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        Category.objects.filter(organization__id=organization_pk, id=category_pk).delete()
        remove(window_info, '#row_category_%s' % category_pk)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_name')
def set_agent_name(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentNameForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        name = value.cleaned_data['name']
        Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).update(name=name)
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_start_time')
def set_agent_start_time(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentStartTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    agent = Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).first()
    if can_update and agent and value and value.is_valid():
        start_time = value.cleaned_data['start_time_1']
        if start_time is None:
            agent.start_time = None
        else:
            agent.start_time = (agent.start_time or datetime.datetime.now(tz=utc)) \
                .replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second)
        agent.save()
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_end_time')
def set_agent_end_time(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentEndTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    agent = Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).first()
    if can_update and agent and value and value.is_valid():
        end_time = value.cleaned_data['end_time_1']
        if end_time is None:
            agent.end_time = None
        else:
            agent.end_time = (agent.end_time or datetime.datetime.now(tz=utc)) \
                .replace(hour=end_time.hour, minute=end_time.minute, second=end_time.second)
        agent.save()
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_start_date')
def set_agent_start_date(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentStartDateForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    agent = Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).first()
    if can_update and agent and value and value.is_valid():
        start_time = value.cleaned_data['start_time_0']
        if start_time is None:
            agent.start_time = None
        else:
            agent.start_time = (agent.start_time or datetime.datetime(1970, 1, 1, hour=0, minute=0, second=0,
                                                                      tzinfo=utc)) \
                .replace(year=start_time.year, month=start_time.month, day=start_time.day)
        agent.save()
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_end_date')
def set_agent_end_date(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentEndDateForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    agent = Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).first()
    if can_update and agent and value and value.is_valid():
        end_time = value.cleaned_data['end_time_0']
        if end_time is None:
            agent.end_time = None
        else:
            agent.end_time = (agent.end_time or datetime.datetime(1970, 1, 1, hour=0, minute=0, second=0, tzinfo=utc)) \
                .replace(year=end_time.year, month=end_time.month, day=end_time.day)
        agent.save()
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_agent')
def add_agent(window_info, organization_pk: int, value: SerializedForm(AgentAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    can_update = organization is not None
    if can_update and value and value.is_valid():
        agent = Agent(organization_id=organization_pk, name=value.cleaned_data['name'])
        agent.save()
        context = {'organization': organization, 'obj': agent}
        content_str = render_to_string('autoplanner/include/agent.html', context=context, window_info=window_info)
        before(window_info, '#row_agent_None', content_str)
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_agent_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_agent')
def remove_agent(window_info, organization_pk: int, agent_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        Agent.objects.filter(organization__id=organization_pk, id=agent_pk).delete()
        remove(window_info, '#row_agent_%s' % agent_pk)
        remove(window_info, '#row_agent_pref_%s' % agent_pk)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.show_agent_infos')
def show_agent_infos(window_info, organization_pk: int, agent_pk: int):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    agent = Agent.objects.filter(organization__id=organization_pk, id=agent_pk).first()
    if organization and agent:
        query = list(AgentCategoryPreferences.objects.filter(organization__id=organization_pk, agent__id=agent_pk)
                     .select_related('category'))
        used_ids = {x.category_id for x in query}
        categories = list(Category.objects.filter(organization=organization).exclude(id__in=used_ids).order_by('name'))
        # noinspection PyProtectedMember
        balancing_modes = Category._meta.get_field('balancing_mode').choices
        if categories:
            agent_category_preferences = AgentCategoryPreferences()
        else:
            agent_category_preferences = None
        context = {'agent_category_preferences': query, 'agent': agent, 'organization': organization,
                   'new_agent_category_preference': agent_category_preferences,
                   'categories': categories, 'balancing_modes': balancing_modes, }
        content_str = render_to_string('autoplanner/include/agent_infos.html', context=context, window_info=window_info)
        modal_show(window_info, content_str)
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa')
    else:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_affinity')
def set_agent_category_preferences_affinity(window_info, organization_pk: int, agent_category_preferences_pk: int,
                                            value: SerializedForm(AgentCategoryPreferencesAffinityForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        affinity = value.cleaned_data['affinity']
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=agent_category_preferences_pk) \
            .update(affinity=affinity)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_balancing_offset')
def set_agent_category_preferences_balancing_offset(window_info, organization_pk: int,
                                                    agent_category_preferences_pk: int,
                                                    value: SerializedForm(AgentCategoryPreferencesBalancingOffsetForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_offset = value.cleaned_data['balancing_offset']
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=agent_category_preferences_pk) \
            .update(balancing_offset=balancing_offset)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_balancing_offset_time')
def set_agent_category_preferences_balancing_offset_time(
        window_info, organization_pk: int,
        agent_category_preferences_pk: int,
        value: SerializedForm(AgentCategoryPreferencesBalancingOffsetTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_offset = value.cleaned_data['balancing_offset'].total_seconds()
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=agent_category_preferences_pk) \
            .update(balancing_offset=balancing_offset)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_balancing_count')
def set_agent_category_preferences_balancing_count(window_info, organization_pk: int,
                                                   agent_category_preferences_pk: int,
                                                   value: SerializedForm(AgentCategoryPreferencesBalancingCountForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_count = value.cleaned_data['balancing_count']
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=agent_category_preferences_pk) \
            .update(balancing_count=balancing_count)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_agent_category_preferences')
def add_agent_category_preferences(window_info, organization_pk: int, agent_pk: int,
                                   value: SerializedForm(AgentCategoryPreferencesAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    agent = Agent.objects.filter(organization__id=organization_pk, id=agent_pk).first()
    AgentCategoryPreferences.objects.filter(organization__id=organization_pk, agent__id=agent_pk) \
        .values_list('category_id')
    if organization and agent and value and value.is_valid():
        new_category_id = value.cleaned_data['category']
        category = Category.objects.filter(organization__id=organization_pk, id=new_category_id).first()
        not_used = AgentCategoryPreferences.objects.filter(organization__id=organization_pk, agent__id=agent_pk,
                                                           category__id=new_category_id).count() == 0
        if not_used and category:
            agent_category_preferences = AgentCategoryPreferences(organization_id=organization_pk, agent_id=agent_pk,
                                                                  category=category)
            agent_category_preferences.save()
            context = {'organization': organization, 'obj': agent_category_preferences, 'agent': agent}
            content_str = render_to_string('autoplanner/include/agent_category_preference.html', context=context,
                                           window_info=window_info)
            before(window_info, '#row_agent_category_preferences_None', content_str)
        if Category.objects.filter(organization__id=organization_pk).count() == \
                AgentCategoryPreferences.objects.filter(organization__id=organization_pk, agent__id=agent_pk).count():
            remove(window_info, '#row_agent_category_preferences_None')
        else:
            remove(window_info, '#id_category option[value="%s"]' % new_category_id)
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_agent_category_preferences_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_agent_category_preferences')
def remove_agent_category_preferences(window_info, organization_pk: int, agent_category_preferences_pk: int,
                                      agent_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, id=agent_category_preferences_pk).delete()
        remove(window_info, '#row_agent_category_preferences_%s' % agent_category_preferences_pk)
        show_agent_infos(window_info, organization_pk=organization_pk, agent_pk=agent_pk)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_task_affectation_mode')
def set_max_task_affectation_mode(window_info, organization_pk: int, max_task_affectation_pk: int,
                                  value: SerializedForm(MaxTaskAffectationModeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        mode = value.cleaned_data['mode']
        MaxTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_task_affectation_pk) \
            .update(mode=mode)
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_task_affectation_category')
def set_max_task_affectation_mode(window_info, organization_pk: int, max_task_affectation_pk: int,
                                  value: SerializedForm(MaxTaskAffectationCategoryForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        category = value.cleaned_data['category']
        MaxTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_task_affectation_pk) \
            .update(category=category)
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_task_affectation_range_time_slice')
def set_max_task_affectation_range_time_slice(window_info, organization_pk: int, max_task_affectation_pk: int,
                                              value: SerializedForm(MaxTaskAffectationRangeTimeSliceForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        range_time_slice = value.cleaned_data['range_time_slice']
        days, hours, seconds = python_to_components(range_time_slice)
        MaxTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_task_affectation_pk) \
            .update(range_time_slice_days=days, range_time_slice_hours=hours, range_time_slice_seconds=seconds)
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_task_affectation_task_maximum_count')
def set_max_task_affectation_task_maximum_count(window_info, organization_pk: int, max_task_affectation_pk: int,
                                                value: SerializedForm(MaxTaskAffectationTaskMaximumCountForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        task_maximum_count = value.cleaned_data['task_maximum_count']
        MaxTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_task_affectation_pk) \
            .update(task_maximum_count=task_maximum_count)
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_task_affectation_%s' % max_task_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_max_task_affectation')
def add_max_task_affectation(window_info, organization_pk: int, value: SerializedForm(MaxTaskAffectationAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if organization and value and value.is_valid():
        new_category_id = value.cleaned_data['category'].id
        category = Category.objects.filter(organization__id=organization_pk, id=new_category_id).first()
        mode = value.cleaned_data['mode']
        range_time_slice = value.cleaned_data['range_time_slice']
        task_maximum_count = value.cleaned_data['task_maximum_count']
        days, hours, seconds = python_to_components(range_time_slice)

        if category:
            max_task_affectation = MaxTaskAffectation(organization_id=organization_pk, mode=mode,
                                                      category=category,
                                                      task_maximum_count=task_maximum_count,
                                                      range_time_slice_days=days, range_time_slice_hours=hours,
                                                      range_time_slice_seconds=seconds)
            max_task_affectation.save()
            context = {'organization': organization, 'obj': max_task_affectation,
                       'categories': Category.objects.filter(organization__id=organization_pk).order_by('name')}
            content_str = render_to_string('autoplanner/include/max_task_affectation.html', context=context,
                                           window_info=window_info)
            before(window_info, '#row_max_task_affectation_None', content_str)
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_max_task_affectation_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_max_task_affectation')
def remove_max_task_affectation(window_info, organization_pk: int, max_task_affectation_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        MaxTaskAffectation.objects \
            .filter(organization__id=organization_pk, id=max_task_affectation_pk).delete()
        remove(window_info, '#row_max_task_affectation_%s' % max_task_affectation_pk)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_time_affectation_mode')
def set_max_time_affectation_mode(window_info, organization_pk: int, max_time_affectation_pk: int,
                                  value: SerializedForm(MaxTaskAffectationModeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        mode = value.cleaned_data['mode']
        MaxTimeTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_time_affectation_pk) \
            .update(mode=mode)
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_time_affectation_category')
def set_max_time_affectation_mode(window_info, organization_pk: int, max_time_affectation_pk: int,
                                  value: SerializedForm(MaxTaskAffectationCategoryForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        category = value.cleaned_data['category']
        MaxTimeTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_time_affectation_pk) \
            .update(category=category)
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_time_affectation_range_time_slice')
def set_max_time_affectation_range_time_slice(window_info, organization_pk: int, max_time_affectation_pk: int,
                                              value: SerializedForm(MaxTaskAffectationRangeTimeSliceForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        range_time_slice = value.cleaned_data['range_time_slice']
        days, hours, seconds = python_to_components(range_time_slice)
        MaxTimeTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_time_affectation_pk) \
            .update(range_time_slice_days=days, range_time_slice_hours=hours, range_time_slice_seconds=seconds)
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_max_time_affectation_task_maximum_time')
def set_max_time_affectation_task_maximum_time(window_info, organization_pk: int, max_time_affectation_pk: int,
                                               value: SerializedForm(MaxTimeAffectationTaskMaximumTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        task_maximum_time = value.cleaned_data['task_maximum_time']
        days, hours, seconds = python_to_components(task_maximum_time)
        MaxTimeTaskAffectation.objects \
            .filter(organization__id=organization_pk, pk=max_time_affectation_pk) \
            .update(task_maximum_time_days=days, task_maximum_time_hours=hours, task_maximum_time_seconds=seconds)
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_max_time_affectation_%s' % max_time_affectation_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_max_time_affectation')
def add_max_time_affectation(window_info, organization_pk: int, value: SerializedForm(MaxTimeAffectationAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if organization and value and value.is_valid():
        new_category_id = value.cleaned_data['category'].id
        category = Category.objects.filter(organization__id=organization_pk, id=new_category_id).first()
        mode = value.cleaned_data['mode']
        range_time_slice = value.cleaned_data['range_time_slice']
        days, hours, seconds = python_to_components(range_time_slice)
        task_maximum_time = value.cleaned_data['task_maximum_time']
        days_, hours_, seconds_ = python_to_components(task_maximum_time)

        if category:
            max_time_affectation = MaxTimeTaskAffectation(organization_id=organization_pk, mode=mode,
                                                          category=category,
                                                          range_time_slice_days=days, range_time_slice_hours=hours,
                                                          range_time_slice_seconds=seconds,
                                                          task_maximum_time_days=days_, task_maximum_time_hours=hours_,
                                                          task_maximum_time_seconds=seconds_)
            max_time_affectation.save()
            context = {'organization': organization, 'obj': max_time_affectation,
                       'categories': Category.objects.filter(organization__id=organization_pk).order_by('name')}
            content_str = render_to_string('autoplanner/include/max_time_affectation.html', context=context,
                                           window_info=window_info)
            before(window_info, '#row_max_time_affectation_None', content_str)
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_max_time_affectation_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_max_time_affectation')
def remove_max_time_affectation(window_info, organization_pk: int, max_time_affectation_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        MaxTimeTaskAffectation.objects \
            .filter(organization__id=organization_pk, id=max_time_affectation_pk).delete()
        remove(window_info, '#row_max_time_affectation_%s' % max_time_affectation_pk)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_name')
def set_task_name(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskNameForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        name = value.cleaned_data['name']
        Task.objects.filter(organization__id=organization_pk, pk=task_pk).update(name=name)
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_start_time')
def set_task_start_time(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskStartTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    task = Task.objects.filter(organization__id=organization_pk, pk=task_pk).first()
    if can_update and task and value and value.is_valid():
        start_time = value.cleaned_data['start_time_1']
        task.start_time = task.start_time.replace(hour=start_time.hour, minute=start_time.minute,
                                                  second=start_time.second)
        task.save()
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_end_time')
def set_task_end_time(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskEndTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    task = Task.objects.filter(organization__id=organization_pk, pk=task_pk).first()
    if can_update and task and value and value.is_valid():
        end_time = value.cleaned_data['end_time_1']
        task.end_time = task.end_time.replace(hour=end_time.hour, minute=end_time.minute, second=end_time.second)
        task.save()
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_start_date')
def set_task_start_date(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskStartDateForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    task = Task.objects.filter(organization__id=organization_pk, pk=task_pk).first()
    if can_update and task and value and value.is_valid():
        start_time = value.cleaned_data['start_time_0']
        task.start_time = task.start_time.replace(year=start_time.year, month=start_time.month, day=start_time.day)
        task.save()
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_end_date')
def set_task_end_date(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskEndDateForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    task = Task.objects.filter(organization__id=organization_pk, pk=task_pk).first()
    if can_update and task and value and value.is_valid():
        end_time = value.cleaned_data['end_time_0']
        task.end_time = task.end_time.replace(year=end_time.year, month=end_time.month, day=end_time.day)
        task.save()
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_agent')
def set_task_agent(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskAgentForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    task = Task.objects.filter(organization__id=organization_pk, pk=task_pk).select_related('agent').first()
    if can_update and task and value and value.is_valid():
        agent = value.cleaned_data['agent']
        if agent:
            Task.objects.filter(organization__id=organization_pk, pk=task_pk).update(fixed=True, agent=agent)
        else:
            Task.objects.filter(organization__id=organization_pk, pk=task_pk).update(fixed=False)
        if agent is None and task.agent:
            content(window_info, '#row_task_%s small.agent' % task_pk,
                    _('Proposed to %(name)s') % {'name': task.agent.name})
        elif agent or task.agent is None:
            content(window_info, '#row_task_%s small.agent' % task_pk, '')

        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_task_categories')
def set_task_categories(window_info, organization_pk: int, task_pk: int, value: SerializedForm(TaskCategoriesForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    task = Task.objects.filter(organization__id=organization_pk, pk=task_pk).select_related('agent').first()
    if can_update and task and value and value.is_valid():
        task.categories = value.cleaned_data['categories']
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_task')
def add_task(window_info, organization_pk: int, value: SerializedForm(TaskAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if organization and value and value.is_valid():
        agent = value.cleaned_data['agent']
        available_category_ids = {x[0] for x in Category.objects.filter(organization=organization).values_list('id')}
        task = Task(organization=organization, name=value.cleaned_data['name'],
                    start_time=value.cleaned_data['start_time'], end_time=value.cleaned_data['end_time'], agent=agent,
                    fixed=bool(agent))
        task.save()
        obj_categories = [x for x in value.cleaned_data['categories'] if x.id in available_category_ids]
        task.categories = obj_categories
        categories = list(Category.objects.filter(organization=organization).order_by('name'))
        agents = list(Agent.objects.filter(organization=organization).order_by('name'))
        context = {'organization': organization, 'obj': task, 'obj_categories': {x.id for x in obj_categories},
                   'agents': agents, 'categories': categories, }
        content_str = render_to_string('autoplanner/include/task.html', context=context,
                                       window_info=window_info)
        before(window_info, '#row_task_None', content_str)
        focus(window_info, '#row_task_None')
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_task_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.filter_tasks')
def filter_tasks(window_info, organization_pk: int, order_by: Choice(Task.orders) = 'start_time',
                 agent_id: int_or_none = None, category_id: int_or_none = None, pattern: str = ''):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if organization:
        change_tab_tasks(window_info, organization, order_by=order_by, agent_id=agent_id, category_id=category_id,
                         pattern=pattern)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.task_multiply')
def task_multiply(window_info, organization_pk: int, task_pk: int, form: SerializedForm(TaskMultiplyForm) = None):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    obj = Task.objects.filter(organization__id=organization_pk, pk=task_pk).first()
    add_attribute(window_info, '#check_task_%s' % task_pk, 'class', 'fa')
    if not organization or not obj:
        return
    if form and form.is_valid():
        until_src = form.cleaned_data['until']
        every_src = form.cleaned_data['every']
        if obj.task_serie:
            task_serie = obj.task_serie
        else:
            obj.task_serie = obj
            obj.save()
            task_serie = obj
        assert isinstance(until_src, datetime.datetime)
        limit = datetime.datetime(year=until_src.year, month=until_src.month, day=until_src.day,
                                  hour=23, minute=59, second=59, tzinfo=obj.start_time.tzinfo)
        tasks_to_create = []
        increment = datetime.timedelta(days=every_src)
        start_time = obj.start_time + increment
        end_time = obj.end_time + increment
        matcher = re.match(r'^(.*)\s+\((\d+)\)', obj.name)
        if matcher:
            new_name = matcher.group(1)
            name_index = int(matcher.group(2)) + 1
        else:
            new_name = obj.name
            name_index = 2
        current_category_pks = [x.pk for x in obj.categories.all()]
        assert isinstance(start_time, datetime.datetime)
        assert isinstance(limit, datetime.datetime)
        while start_time < limit:
            new_task = Task(organization_id=obj.organization_id, name='%s (%d)' % (new_name, name_index),
                            start_time=start_time, end_time=end_time, task_serie=task_serie)
            tasks_to_create.append(new_task)
            start_time += increment
            end_time += increment
            name_index += 1
        if tasks_to_create:
            cls = Task.categories.through
            all_categories_to_create = []
            for new_task in tasks_to_create:
                new_task.save()
                all_categories_to_create += [cls(task_id=new_task.pk, category_id=category_pk)
                                             for category_pk in current_category_pks]
            cls.objects.bulk_create(all_categories_to_create)
        if len(tasks_to_create) > 1:
            notify(window_info, _('%(count)d tasks have been created.') % {'count': len(tasks_to_create)}, level=INFO)
        elif tasks_to_create:
            notify(window_info, _('A task has been created.'), level=INFO)

        # add the task to the HTML page
        categories = list(Category.objects.filter(organization=organization).order_by('name'))
        agents = list(Agent.objects.filter(organization=organization).order_by('name'))
        context = {'organization': organization, 'obj': None, 'obj_categories': current_category_pks,
                   'agents': agents, 'categories': categories, }
        for new_task in tasks_to_create:
            context['obj'] = new_task
            content_str = render_to_string('autoplanner/include/task.html', context=context, window_info=window_info)
            before(window_info, '#row_task_None', content_str)
        modal_hide(window_info)
        return
    elif not form:
        form = TaskMultiplyForm()
    context = {'task': obj, 'organization': organization, 'form': form}
    content_str = render_to_string('autoplanner/include/task_multiply.html', context=context, window_info=window_info)
    modal_show(window_info, content_str)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_task')
def remove_task(window_info, organization_pk: int, task_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        Task.objects.filter(organization__id=organization_pk, id=task_pk).delete()
        remove(window_info, '#row_task_%s' % task_pk)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.task_multiple_update_show')
def task_multiple_update_show(window_info, organization_pk: int):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    categories = list(Category.objects.filter(organization=organization).order_by('name'))
    agents = list(Agent.objects.filter(organization=organization).order_by('name'))
    context = {'organization': organization, 'categories': categories, 'agents': agents}
    content_str = render_to_string('autoplanner/include/task_multiple_update.html', context=context,
                                   window_info=window_info)
    modal_show(window_info, content_str)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.task_multiple_update')
def task_multiple_update(window_info, organization_pk: int, form: SerializedForm(TaskMultipleUpdateForm) = None,
                         order_by: Choice(Task.orders) = 'start_time', agent_id: int_or_none = None,
                         category_id: int_or_none = None, pattern: str = ''):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    if form and form.is_valid():
        agent = form.cleaned_data['agent']
        category_ids = {x.id for x in form.cleaned_data['categories']}
        task_ids = {x.id for x in form.cleaned_data['tasks']}
        kwargs = {}
        if agent:
            kwargs['fixed'] = True
            kwargs['agent'] = agent
        elif form.cleaned_data['fix']:
            kwargs['fixed'] = True
        elif form.cleaned_data['unfix']:
            kwargs['fixed'] = False
        if kwargs:
            Task.objects.filter(id__in=task_ids).update(**kwargs)
        if category_ids:
            cls = Task.categories.through
            cls.objects.filter(task_id__in=task_ids).delete()
            all_categories_to_create = []
            for task_id in task_ids:
                all_categories_to_create += [cls(task_id=task_id, category_id=pk) for pk in category_ids]
            cls.objects.bulk_create(all_categories_to_create)
        change_tab_tasks(window_info, organization, order_by=order_by, agent_id=agent_id, category_id=category_id,
                         pattern=pattern)
    modal_hide(window_info)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.task_multiple_remove')
def task_multiple_remove(window_info, organization_pk: int, form: SerializedForm(TaskMultipleRemoveForm) = None,
                         order_by: Choice(Task.orders) = 'start_time', agent_id: int_or_none = None,
                         category_id: int_or_none = None, pattern: str = ''):
    # noinspection PyUnusedLocal
    order_by, agent_id, category_id, pattern = order_by, agent_id, category_id, pattern
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    if form and form.is_valid():
        task_ids = {x.id for x in form.cleaned_data['tasks']}
        Task.objects.filter(organization__id=organization_pk, id__in=task_ids).delete()
        for task_id in task_ids:
            remove(window_info, '#row_task_%s' % task_id)
    modal_hide(window_info)


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.task_import')
def task_import(window_info, organization_pk: int, form: SerializedForm(TaskImportForm) = None,
                order_by: Choice(Task.orders) = 'start_time', agent_id: int_or_none = None,
                category_id: int_or_none = None, pattern: str = ''):
    # noinspection PyUnusedLocal
    order_by, agent_id, category_id, pattern = order_by, agent_id, category_id, pattern
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    if form and form.is_valid():
        csv_reader = csv.reader(form.cleaned_data['csv_content'].splitlines(), delimiter=';')
        task_categories_to_create = []
        categories = list(Category.objects.filter(organization=organization).order_by('name'))
        agents = list(Agent.objects.filter(organization=organization).order_by('name'))
        name_to_category = {x.name: x.id for x in categories}
        name_to_agent = {x.name: x.id for x in agents}
        cls = Task.categories.through
        context = {'organization': organization, 'agents': agents, 'categories': categories, }
        counter = 0
        date_field, time_field = forms.DateField(), forms.TimeField()

        def read_value(value, field):
            try:
                return field.to_python(value)
            except ValueError:
                notify(window_info, _('%(v)d is invalid.') % {'v': value}, level=DANGER)
                return None

        def combine(d, t):
            if d is None or t is None:
                return None
            return datetime.datetime.combine(d, t).replace(tzinfo=utc)

        for row in csv_reader:
            if len(row) != 7:
                continue
            start_date, start_time = read_value(row[1], date_field), read_value(row[2], time_field)
            end_date, end_time = read_value(row[3], date_field), read_value(row[4], time_field)
            start = combine(start_date, start_time)
            end = combine(end_date, end_time)
            if start is None or end is None:
                continue
            category_ids = {name_to_category[x.strip()] for x in row[5].split('/') if x.strip() in name_to_category}
            agent_id = name_to_agent.get(row[6].strip())
            task = Task(name=row[0].strip(), fixed=bool(agent_id), agent_id=agent_id, start_time=start, end_time=end,
                        organization_id=organization_pk)
            task.save()
            task_categories_to_create += [cls(task_id=task.pk, category_id=x) for x in category_ids]
            context['obj_categories'] = category_ids
            context['obj'] = task
            content_str = render_to_string('autoplanner/include/task.html', context=context, window_info=window_info)
            before(window_info, '#row_task_None', content_str)
            counter += 1
        cls.objects.bulk_create(task_categories_to_create)
        if counter > 1:
            notify(window_info, _('%(count)d tasks have been created.') % {'count': counter}, level=INFO)
        elif counter:
            notify(window_info, _('A task has been created.'), level=INFO)
        modal_hide(window_info)

        return
    example_1 = datetime.datetime.now(tz=utc)
    example_2 = datetime.datetime.now(tz=utc) + datetime.timedelta(days=7)
    example_c = '/'.join([x[0] for x in Category.objects.filter(organization=organization).values_list('name')])
    resources = list(Agent.objects.filter(organization=organization)[0:2].values_list('name'))
    if resources:
        example_a, example_b = resources[0][0], resources[-1][0]
    else:
        example_a, example_b = _('Resource A'), _('Resource B')
    context = {'organization': organization, 'example_c': example_c, 'example_1': example_1, 'example_2': example_2,
               'example_a': example_a, 'example_b': example_b}
    content_str = render_to_string('autoplanner/include/task_import.html', context=context, window_info=window_info)
    modal_show(window_info, content_str)


@signal(is_allowed_to=is_authenticated, path='autoplanner.schedule.launch')
def schedule_launch(window_info, organization_pk: int):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    compute_schedule.delay(organization_pk, window_info.to_dict())


@signal(is_allowed_to=is_authenticated, path='autoplanner.schedule.kill')
def schedule_kill(window_info, organization_pk: int, celery_task_id: str):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    kill_schedule.delay(celery_task_id, window_info.to_dict())


@signal(is_allowed_to=is_authenticated, path='autoplanner.schedule.remove')
def schedule_remove(window_info, organization_pk: int, schedule_pk: int):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if organization:
        ScheduleRun.objects.filter(organization__id=organization_pk, id=schedule_pk).delete()
        remove(window_info, '#schedule_%s' % schedule_pk)


def change_tab_schedule(window_info, organization):
    context = prepare_schedule_stats(organization)
    render_to_client(window_info, 'autoplanner/tabs/schedule.html', context, '#schedule')


def prepare_schedule_stats(organization):
    scheduler = Scheduler(organization)
    statistics = {x.pk: {category.pk: [0, datetime.timedelta(0), None] for category in scheduler.categories}
                  for x in scheduler.agents}
    # [total_number, total_time, balanced_value]
    # first we add the offset (multiplied by the balancing coefficient)
    for category in scheduler.categories:
        if category.balancing_mode == Category.BALANCE_NUMBER:
            for agent in scheduler.agents:
                offset, count, __ = scheduler.preferences_by_agent_by_category[category.pk].get(agent.pk, (0., 1., 0.))
                if count is None:
                    statistics[agent.pk][category.pk][2] = None
                else:
                    statistics[agent.pk][category.pk][2] = offset * count
        elif category.balancing_mode == Category.BALANCE_TIME:
            for agent in scheduler.agents:
                offset, count, __ = scheduler.preferences_by_agent_by_category[category.pk].get(agent.pk, (0., 1., 0.))
                if count is None:
                    statistics[agent.pk][category.pk][2] = None
                else:
                    statistics[agent.pk][category.pk][2] = datetime.timedelta(seconds=offset * count)
    # we can add all the tasks
    for task in scheduler.tasks:
        if task.agent_id is None:
            continue
        for category_pk in scheduler.categories_by_task[task.pk]:
            duration = task.duration
            statistics[task.agent_id][category_pk][0] += 1
            statistics[task.agent_id][category_pk][1] += duration
            if scheduler.categories_by_pk[category_pk].balancing_mode is None:
                continue
            __, count, __ = scheduler.preferences_by_agent_by_category[category_pk].get(task.agent_id, (0., 1., 0.))
            if scheduler.categories_by_pk[category_pk].balancing_mode == Category.BALANCE_NUMBER:
                if count is None:
                    statistics[task.agent_id][category_pk][2] = None
                else:
                    statistics[task.agent_id][category_pk][2] += count

            elif scheduler.categories_by_pk[category_pk].balancing_mode == Category.BALANCE_TIME:
                value = datetime.timedelta(seconds=duration.total_seconds() * count)
                statistics[task.agent_id][category_pk][2] += value
    categories = [category for category in scheduler.categories]
    categories.sort(key=lambda x: x.name)
    agents = [agent for agent in scheduler.agents]
    agents.sort(key=lambda x: x.name)
    sorted_statistics = [[x] + [statistics[x.pk][y.pk] for y in categories] for x in agents]
    context = {'obj': organization, 'statistics': sorted_statistics, 'agents': agents,
               'categories': categories, 'description': markdown.markdown(organization.description),
               'api_key_variable': API_KEY_VARIABLE, 'organization': organization}
    return context


@signal(is_allowed_to=is_authenticated, path='autoplanner.calendar.month')
def calendar_month(window_info, organization_pk: int, year: int=None, month: int=None):
    now = datetime.datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    if not 1970 <= year <= 2050 or not 1 <= month <= 12:
        return
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    # cal = calendar.LocaleTextCalendar(locale=settings.LANGUAGE_CODE)
    month_matrix = calendar.monthcalendar(year, month)
    start = datetime.datetime(year, month, 1, 0, 0, 0, tzinfo=utc)
    end = datetime.datetime(year, month, max(month_matrix[-1]), 23, 59, 59, tzinfo=utc)
    query = Task.objects.filter(organization=organization).exclude(end_time__lt=start)\
        .exclude(start_time__gt=end).select_related('agent').prefetch_related('categories')
    task_matrix = [[(x, []) for x in line] for line in month_matrix]
    # task_matrix[row][col] = [day number or 0, [list of tasks]]
    offset = len(list(filter(lambda x: x == 0, task_matrix[0])))
    for task in query:
        s = max(task.start_time, start)
        e = min(task.end_time, end)
        for day in range(s.day, e.day + 1):
            col = ((day + offset) % 7 or 7) - 1
            row = (day + offset - col - 1) // 7
            task_matrix[row][col][1].append(task)
    previous_year, previous_month = year, month - 1
    if previous_month == 0:
        previous_year -= 1
        previous_month = 12
    next_year, next_month = year, month + 1
    if next_month == 13:
        next_year += 1
        next_month = 1
    month_str = {1: _('January'), 2: _('February'), 3: _('March'), 4: _('April'),
                 5: _('May'), 6: _('June'), 7: _('July'), 8: _('August'),
                 9: _('September'), 10: _('October'), 11: _('November'), 12: _('December')}[month]
    context = {'matrix': task_matrix, 'month': month, 'year': year, 'organization': organization,
               'previous_month': previous_month, 'previous_year': previous_year,
               'next_year': next_year, 'next_month': next_month, 'month_str': month_str}
    render_to_client(window_info, 'autoplanner/calendars/by_month.html', context, '#schedule')


@signal(is_allowed_to=is_authenticated, path='autoplanner.calendar.week')
def calendar_week(window_info, organization_pk: int, year: int=None, month: int=None, day: int=None):
    now = datetime.datetime.now()
    try:
        start = datetime.datetime(year or now.year, month or now.month, day or now.day, tzinfo=utc)
    except ValueError:
        return
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    start -= datetime.timedelta(days=(start.isoweekday() - 1))
    end = start + datetime.timedelta(days=7)
    month_str = {1: _('January'), 2: _('February'), 3: _('March'), 4: _('April'),
                 5: _('May'), 6: _('June'), 7: _('July'), 8: _('August'),
                 9: _('September'), 10: _('October'), 11: _('November'), 12: _('December')}[start.month]
    task_matrix = [[(x, []) for x in range(7)] for y in range(24)]
    query = Task.objects.filter(organization=organization).exclude(end_time__lt=start)\
        .exclude(start_time__gt=end).select_related('agent').prefetch_related('categories')
    duration = datetime.timedelta(hours=1)
    for task in query:
        s = max(task.start_time, start).replace(minute=0, second=0)
        e = min(task.end_time, end)
        while s < e:
            col = s.isoweekday() - 1
            row = s.hour
            s += duration
            if 0 <= row <= 23 and 0 <= col <= 6:
                task_matrix[row][col][1].append(task)
    col_days = [(start + datetime.timedelta(days=x)).day for x in range(7)]
    previous_start = start - datetime.timedelta(days=7)
    context = {'matrix': task_matrix, 'month': start.month, 'year': start.year, 'organization': organization,
               'start': start, 'end': end, 'previous_week': previous_start, 'next_week': end, 'month_str': month_str,
               'col_days': col_days}
    render_to_client(window_info, 'autoplanner/calendars/by_week.html', context, '#schedule')


@signal(is_allowed_to=is_authenticated, path='autoplanner.schedule.apply')
def schedule_apply(window_info, organization_pk: int, schedule_pk: int):
    organization = Organization.query(window_info).filter(pk=organization_pk).select_related('current_schedule').first()
    if not organization:
        return
    schedule_run = ScheduleRun.objects.filter(organization__id=organization_pk, pk=schedule_pk).first()
    old_schedule_run = organization.current_schedule
    if not schedule_run or not schedule_run.result_dict:
        return
    result_dict = json.loads(schedule_run.result_dict)
    try:
        apply_schedule(organization_pk, result_dict)
    except ValueError as e:
        notify(window_info, str(e), style=NOTIFICATION, level=DANGER)
        return
    Organization.objects.filter(pk=organization_pk).update(current_schedule_id=schedule_pk)
    ScheduleRun.objects.filter(organization__id=organization_pk).exclude(pk=schedule_pk)\
        .update(is_selected=False)
    ScheduleRun.objects.filter(pk=schedule_pk).update(is_selected=True)
    schedule_run.is_selected = True
    if old_schedule_run:
        old_schedule_run.is_selected = False
        content_str = render_to_string('autoplanner/include/schedule.html',
                                       context={'obj': old_schedule_run, 'organization': organization})
        replace_with(window_info, '#schedule_%s' % old_schedule_run.id, content_str)
    content_str = render_to_string('autoplanner/include/schedule.html',
                                   context={'obj': schedule_run, 'organization': organization})
    replace_with(window_info, '#schedule_%s' % schedule_run.id, content_str)


@signal(is_allowed_to=is_authenticated, path='autoplanner.schedule.info')
def schedule_info(window_info, organization_pk: int):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    if not organization:
        return
    context = prepare_schedule_stats(organization)
    content_str = render_to_string('autoplanner/include/schedule_info.html',
                                   context=context, window_info=window_info)
    modal_show(window_info, content_str)
