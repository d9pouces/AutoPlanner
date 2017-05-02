# -*- coding: utf-8 -*-
from djangofloor.decorators import signal, is_authenticated, everyone, SerializedForm
from djangofloor.signals.html import render_to_client, add_attribute, remove_class, add_class

from autoplanner.forms import OrganizationDescriptionForm, OrganizationAccessTokenForm, OrganizationMaxComputeTimeForm, \
    CategoryFormSet, CategoryForm, CategoryNameForm, CategoryBalancingModeForm, CategoryBalancingToleranceForm, \
    CategoryAutoAffinityForm
from autoplanner.models import Organization, default_token, Category

__author__ = 'Matthieu Gallet'


@signal(is_allowed_to=everyone, path='autoplanner.change_tab', queue='fast')
def change_tab(window_info, organization_pk: int, tab_name: str):
    obj = Organization.query(window_info).filter(pk=organization_pk).first()
    fn = {'general': change_tab_general, 'categories': change_tab_categories}.get(tab_name)
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
               'balancing_modes': balancing_modes}
    render_to_client(window_info, 'autoplanner/tabs/categories.html', context, '#categories')


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
def set_category_balancing_mode(window_info, organization_pk: int, category_pk: int,
                                value: SerializedForm(CategoryBalancingModeForm)):
    can_update = Organization.query(window_info).filter(pk=organization_pk).count() > 0
    if can_update and value and value.is_valid():
        balancing_mode = value.cleaned_data['balancing_mode']
        Category.objects.filter(organization__id=organization_pk, pk=category_pk)\
            .update(balancing_mode=balancing_mode or None)
        add_attribute(window_info, '#check_category_%s' % category_pk, 'class', 'fa fa-check')
        if balancing_mode:
            remove_class(window_info, '#id_balancing_tolerance_%s' % category_pk, 'hidden')
        else:
            add_class(window_info, '#id_balancing_tolerance_%s' % category_pk, 'hidden')
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
def add_category(window_info, organization_pk: int, value: SerializedForm(CategoryForm)):
    pass
