# -*- coding: utf-8 -*-
from djangofloor.decorators import signal, is_authenticated, everyone, SerializedForm
from djangofloor.signals.bootstrap3 import notify, NOTIFICATION, DANGER, modal_show
from djangofloor.signals.html import render_to_client, add_attribute, remove_class, add_class, remove, before, focus, \
    content
from djangofloor.wsgi.window_info import render_to_string

from autoplanner.forms import OrganizationDescriptionForm, OrganizationAccessTokenForm, OrganizationMaxComputeTimeForm, \
    CategoryNameForm, CategoryBalancingModeForm, CategoryBalancingToleranceForm, \
    CategoryAutoAffinityForm, CategoryAddForm, AgentAddForm, AgentNameForm, AgentStartTimeForm, AgentEndTimeForm, \
    AgentCategoryPreferencesAffinityForm, AgentCategoryPreferencesAddForm
from autoplanner.models import Organization, default_token, Category, Agent, AgentCategoryPreferences

__author__ = 'Matthieu Gallet'


@signal(is_allowed_to=everyone, path='autoplanner.change_tab', queue='fast')
def change_tab(window_info, organization_pk: int, tab_name: str):
    obj = Organization.query(window_info).filter(pk=organization_pk).first()
    fn = {'general': change_tab_general, 'categories': change_tab_categories,
          'agents': change_tab_agents}.get(tab_name)
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
    form = AgentStartTimeForm()
    context = {'organization': organization, 'agents': queryset, 'new_agent': Agent(),
               'form': form}
    render_to_client(window_info, 'autoplanner/tabs/agents.html', context, '#agents')


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
        if balancing_mode:
            remove_class(window_info, '#id_balancing_tolerance_%s' % category_pk, 'hidden')
            if balancing_mode == Category.BALANCE_TIME:
                remove_class(window_info, '#time_balancing_tolerance_%s' % category_pk, 'hidden')
                add_class(window_info, '#units_balancing_tolerance_%s' % category_pk, 'hidden')
            else:
                add_class(window_info, '#time_balancing_tolerance_%s' % category_pk, 'hidden')
                remove_class(window_info, '#units_balancing_tolerance_%s' % category_pk, 'hidden')
        else:
            add_class(window_info, '#id_balancing_tolerance_%s' % category_pk, 'hidden')
            add_class(window_info, '#time_balancing_tolerance_%s' % category_pk, 'hidden')
            add_class(window_info, '#units_balancing_tolerance_%s' % category_pk, 'hidden')
    elif value:
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_category_balancing_tolerance')
def set_category_balancing_tolerance(window_info, organization_pk: int, category_pk: int,
                                     value: SerializedForm(CategoryBalancingToleranceForm)):
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
        context = {'organization': organization, 'balancing_modes': balancing_modes, 'category': category}
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


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_start_time')
def set_agent_start_time(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentStartTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        start_time = value.cleaned_data['start_time']
        Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).update(start_time=start_time)
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_end_time')
def set_agent_end_time(window_info, organization_pk: int, agent_pk: int, value: SerializedForm(AgentEndTimeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        end_time = value.cleaned_data['end_time']
        Agent.objects.filter(organization__id=organization_pk, pk=agent_pk).update(end_time=end_time)
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
        query = AgentCategoryPreferences.objects.filter(organization__id=organization_pk, agent__id=agent_pk) \
            .select_related('category')
        categories = list(Category.objects.filter(organization=organization).order_by('name'))
        # noinspection PyProtectedMember
        balancing_modes = Category._meta.get_field('balancing_mode').choices
        context = {'agent_category_preferences': query, 'agent': agent, 'organization': organization,
                   'new_agent_category_preference': AgentCategoryPreferences(),
                   'categories': categories, 'balancing_modes': balancing_modes, }
        content_str = render_to_string('autoplanner/include/agent_infos.html', context=context, window_info=window_info)
        modal_show(window_info, content_str)
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa')
    else:
        add_attribute(window_info, '#check_agent_%s' % agent_pk, 'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_affinity')
def set_agent_category_preferences_affinity(window_info, organization_pk: int, check_agent_category_preferences_pk: int,
                                            value: SerializedForm(AgentCategoryPreferencesAffinityForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        affinity = value.cleaned_data['affinity']
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=check_agent_category_preferences_pk) \
            .update(affinity=affinity)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % check_agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % check_agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_balancing_offset')
def set_agent_category_preferences_balancing_offset(window_info, organization_pk: int,
                                                    check_agent_category_preferences_pk: int,
                                                    value: SerializedForm(AgentCategoryPreferencesAffinityForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_offset = value.cleaned_data['balancing_offset']
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=check_agent_category_preferences_pk) \
            .update(balancing_offset=balancing_offset)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % check_agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % check_agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.set_agent_category_preferences_balancing_count')
def set_agent_category_preferences_balancing_count(window_info, organization_pk: int,
                                                   check_agent_category_preferences_pk: int,
                                                   value: SerializedForm(AgentCategoryPreferencesAffinityForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_count = value.cleaned_data['balancing_count']
        AgentCategoryPreferences.objects \
            .filter(organization__id=organization_pk, pk=check_agent_category_preferences_pk) \
            .update(balancing_count=balancing_count)
        add_attribute(window_info, '#check_agent_category_preferences_%s' % check_agent_category_preferences_pk,
                      'class', 'fa fa-check')
    elif value:
        add_attribute(window_info, '#check_agent_category_preferences_%s' % check_agent_category_preferences_pk,
                      'class', 'fa fa-remove')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.add_agent_category_preferences')
def add_agent_category_preferences(window_info, organization_pk: int, agent_pk: int,
                                   value: SerializedForm(AgentCategoryPreferencesAddForm)):
    organization = Organization.query(window_info).filter(pk=organization_pk).first()
    agent = Agent.objects.filter(organization__id=organization_pk, id=agent_pk).first()
    if organization and agent and value and value.is_valid():
        agent_category_preferences = AgentCategoryPreferences(organization_id=organization_pk, agent_id=agent_pk,
                                                              name=value.cleaned_data['name'])
        agent_category_preferences.save()
        context = {'organization': organization, 'agent_category_preferences': agent_category_preferences}
        content_str = render_to_string('autoplanner/include/agent_category_preference.html', context=context,
                                       window_info=window_info)
        before(window_info, '#row_agent_category_preferences_None', content_str)
    elif value and not value.is_valid():
        notify(window_info, value.errors, style=NOTIFICATION, level=DANGER)
    add_attribute(window_info, '#check_agent_category_preferences_None', 'class', 'fa')
    focus(window_info, '#id_name_None')


@signal(is_allowed_to=is_authenticated, path='autoplanner.forms.remove_agent_category_preferences')
def remove_agent_category_preferences(window_info, organization_pk: int, agent_category_preferences_pk: int):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update:
        Agent.objects.filter(organization__id=organization_pk, id=agent_category_preferences_pk).delete()
        remove(window_info, '#row_agent_category_preferences_%s' % agent_category_preferences_pk)
