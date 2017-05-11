# -*- coding: utf-8 -*-
import datetime

from django.utils.timezone import utc
from djangofloor.decorators import signal, is_authenticated, everyone, SerializedForm
from djangofloor.signals.bootstrap3 import notify, NOTIFICATION, DANGER, modal_show
from djangofloor.signals.html import render_to_client, add_attribute, remove_class, add_class, remove, before, focus
from djangofloor.wsgi.window_info import render_to_string

from autoplanner.forms import OrganizationDescriptionForm, OrganizationAccessTokenForm, OrganizationMaxComputeTimeForm, \
    CategoryNameForm, CategoryBalancingModeForm, CategoryAutoAffinityForm, CategoryAddForm, AgentAddForm, AgentNameForm, \
    AgentStartTimeForm, AgentEndTimeForm, \
    AgentCategoryPreferencesAffinityForm, AgentCategoryPreferencesAddForm, AgentCategoryPreferencesBalancingOffsetForm, \
    AgentCategoryPreferencesBalancingCountForm, MaxTaskAffectationAddForm, MaxTaskAffectationModeForm, \
    MaxTaskAffectationCategoryForm, MaxTaskAffectationTaskMaximumCountForm, MaxTaskAffectationRangeTimeSliceForm, \
    AgentCategoryPreferencesBalancingOffsetTimeForm, MaxTimeAffectationTaskMaximumTimeForm, MaxTimeAffectationAddForm, \
    CategoryBalancingToleranceTimeForm, CategoryBalancingToleranceNumberForm, AgentStartDateForm, AgentEndDateForm
from autoplanner.models import Organization, default_token, Category, Agent, AgentCategoryPreferences, \
    MaxTaskAffectation, MaxTimeTaskAffectation
from autoplanner.utils import python_to_components

__author__ = 'Matthieu Gallet'


@signal(is_allowed_to=everyone, path='autoplanner.change_tab', queue='fast')
def change_tab(window_info, organization_pk: int, tab_name: str):
    obj = Organization.query(window_info).filter(pk=organization_pk).first()
    fn = {'general': change_tab_general, 'categories': change_tab_categories,
          'agents': change_tab_agents, 'balancing': change_tab_balancing,
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
            balancing_tolerance=balancing_tolerance.total_seconds())
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
            balancing_tolerance=balancing_tolerance)
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
        agent.start_time = (agent.start_time or datetime.datetime.now(tz=utc))\
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
        agent.end_time = (agent.end_time or datetime.datetime.now(tz=utc))\
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

        agent.start_time = (agent.start_time or datetime.datetime(1970, 1, 1, hour=0, minute=0, second=0, tzinfo=utc))\
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
        agent.end_time = (agent.end_time or datetime.datetime(1970, 1, 1, hour=0, minute=0, second=0, tzinfo=utc))\
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
        context = {'organization': organization, 'agent': agent}
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
