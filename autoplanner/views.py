# -*- coding: utf-8 -*-
import datetime
from django.views.decorators.cache import never_cache
import re

from django.contrib import admin
from django.contrib.admin.options import IS_POPUP_VAR, get_content_type_for_model
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib import messages
from django.contrib.admin.utils import quote
from django.core.urlresolvers import reverse
from django.http.response import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from djangofloor.celery import app
from icalendar import Calendar, Event
import markdown

from autoplanner.admin import OrganizationAdmin
from autoplanner.forms import MultiplyTaskForm
from autoplanner.models import Organization, Task, Category, Agent, API_KEY_VARIABLE
from autoplanner.schedule import Scheduler
from autoplanner.tasks import compute_schedule

__author__ = 'Matthieu Gallet'


def get_template_values(request, organization_pk):
    org = get_object_or_404(Organization.query(request, readonly=True), pk=organization_pk)
    assert isinstance(org, Organization)
    # noinspection PyProtectedMember
    model_admin = admin.site._registry[Organization]
    assert isinstance(model_admin, OrganizationAdmin)
    # noinspection PyProtectedMember
    opts = model_admin.model._meta
    app_label = opts.app_label
    preserved_filters = model_admin.get_preserved_filters(request)
    form_url = add_preserved_filters({'preserved_filters': preserved_filters, 'opts': opts}, '?')
    view_on_site_url = model_admin.get_view_on_site_url(org)
    template_values = {
        'is_popup': 0,
        'add': False,
        'change': True,
        'has_change_permission': model_admin.has_change_permission(request, org),
        'has_delete_permission': False,
        'has_add_permission': False,
        'has_file_field': False,
        'has_absolute_url': view_on_site_url is not None,
        'absolute_url': view_on_site_url,
        'form_url': form_url,
        'opts': opts,
        'content_type_id': get_content_type_for_model(Task).pk,
        'save_as': True,
        'save_on_top': False,
        'media': model_admin.media,
        'to_field_var': TO_FIELD_VAR,
        'is_popup_var': IS_POPUP_VAR,
        'app_label': app_label,
        'show_save': False,
    }
    return template_values


@never_cache
def organization(request, organization_pk):
    template_values = get_template_values(request, organization_pk)
    obj = get_object_or_404(Organization.query(request, readonly=True), pk=organization_pk)
    scheduler = Scheduler(obj)
    messages.info(request, obj.message)
    statistics = {x.pk: {category.pk: [0, datetime.timedelta(0), None] for category in scheduler.categories}
                  for x in scheduler.agents}
    # [total_number, total_time, balanced_value]
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
    template_values.update({
        'obj': obj,
        'statistics': sorted_statistics,
        'agents': agents,
        'categories': categories,
        'description': markdown.markdown(obj.description),
        'api_key_variable': API_KEY_VARIABLE,
    })
    return render_to_response('autoplanner/organization.html', template_values, RequestContext(request))


@never_cache
def multiply_task(request, task_pk):
    obj = get_object_or_404(Task.query(request), pk=task_pk)
    # noinspection PyProtectedMember
    model_admin = admin.site._registry[Organization]
    assert isinstance(model_admin, OrganizationAdmin)
    # noinspection PyProtectedMember
    opts = model_admin.model._meta
    if request.method == 'POST':
        form = MultiplyTaskForm(request.POST)
        if form.is_valid():
            until_src = form.cleaned_data['until']
            every_src = form.cleaned_data['every']
            assert isinstance(until_src, datetime.datetime)
            limit = datetime.datetime(year=until_src.year, month=until_src.month, day=until_src.day,
                                      hour=23, minute=59, second=59, tzinfo=obj.start_time.tzinfo)
            to_create = []
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
            while start_time < limit:
                new_task = Task(organization_id=obj.organization_id, name='%s (%d)' % (new_name, name_index),
                                start_time=start_time, end_time=end_time)
                to_create.append(new_task)
                start_time += increment
                end_time += increment
                name_index += 1
            if to_create:
                if current_category_pks:
                    cls = Task.categories.through
                    all_categories_to_create = []
                    for new_task in to_create:
                        new_task.save()
                        all_categories_to_create += [cls(task_id=new_task.pk, category_id=category_pk)
                                                     for category_pk in current_category_pks]
                    cls.objects.bulk_create(all_categories_to_create)
                else:
                    Task.objects.bulk_create(to_create)
            if len(to_create) > 1:
                messages.info(request, _('%(count)d tasks have been created.') % {'count': len(to_create)})
            elif to_create:
                messages.info(request, _('A task has been created.'))
            new_url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                              args=(quote(obj.organization_id), ), current_app=model_admin.admin_site.name)
            return HttpResponseRedirect(new_url)
    else:
        form = MultiplyTaskForm(initial={'source_task': obj})
    template_values = get_template_values(request, organization_pk=obj.organization_id)
    template_values['obj'] = obj
    template_values['form'] = form
    return render_to_response('autoplanner/multiply_task.html', template_values, RequestContext(request))


@never_cache
def schedule_task(request, organization_pk):
    obj = get_object_or_404(Organization.query(request), pk=organization_pk)
    # noinspection PyProtectedMember
    model_admin = admin.site._registry[Organization]
    assert isinstance(model_admin, OrganizationAdmin)
    # noinspection PyProtectedMember
    opts = model_admin.model._meta
    count = Organization.objects.filter(pk=organization_pk, celery_task_id=None)
    if count == 0:
        messages.error(request, _('%(obj)s is already busy.') % {'obj': obj})
    else:
        compute_schedule.delay(obj.pk)
        messages.info(request, _('Computation launched.') % {'obj': obj})
    new_url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                      args=(quote(obj.pk), ), current_app=model_admin.admin_site.name)
    return HttpResponseRedirect(new_url)


@never_cache
def cancel_schedule_task(request, organization_pk):
    obj = get_object_or_404(Organization.query(request), pk=organization_pk)
    # noinspection PyProtectedMember
    model_admin = admin.site._registry[Organization]
    assert isinstance(model_admin, OrganizationAdmin)
    # noinspection PyProtectedMember
    opts = model_admin.model._meta
    if obj.celery_task_id is None:
        messages.error(request, _('No computation is running on %(obj)s.') % {'obj': obj})
    else:
        app.control.revoke(obj.celery_task_id)
        obj.celery_task_id = None
        obj.save()
        messages.info(request, _('Computation has been interrupted.') % {'obj': obj})
    new_url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                      args=(quote(obj.pk), ), current_app=model_admin.admin_site.name)
    return HttpResponseRedirect(new_url)


@never_cache
def generate_ics(request, organization_pk, agent_pk=None, category_pk=None):
    obj = get_object_or_404(Organization.query(request, readonly=True), pk=organization_pk)
    cal = Calendar()
    cal.add('prodid', '-//AutoPlanner//19pouces.net//')
    cal.add('version', '2.0')
    query = Task.objects.filter(organization=obj)
    if agent_pk:
        query = query.filter(agent__id=agent_pk)
    if category_pk:
        query = query.filter(categories__id=category_pk)
    agents = {x.pk: x.name for x in Agent.objects.filter(organization=obj)}
    for task in query:
        event = Event()
        if task.agent_id:
            summary = '%s (%s)' % (task.name, agents[task.agent_id])
        else:
            summary = task.name
        event.add('summary', summary)
        event.add('dtstart', task.start_time)
        event.add('dtend', task.end_time)
        event['uid'] = task.start_time.strftime('%Y%m%dT%H%M%S-') + str(task.pk)
        cal.add_component(event)
    return HttpResponse(cal.to_ical(), content_type='text/calendar')