import datetime
import json

import markdown
from django.conf import settings
from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.options import IS_POPUP_VAR, get_content_type_for_model
from django.contrib.admin.options import TO_FIELD_VAR
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote
from django.db.models import F
from django.http.response import HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404
from django.template import RequestContext
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils.formats import date_format
from django.utils.formats import time_format
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from djangofloor.tasks import set_websocket_topics
from icalendar import Calendar, Event

from autoplanner.admin import OrganizationAdmin
from autoplanner.forms import OrganizationAddForm
from autoplanner.models import Organization, Task, Category, Agent, API_KEY_VARIABLE, ScheduleRun
from autoplanner.schedule import Scheduler
from autoplanner.tasks import compute_schedule, kill_schedule, apply_schedule

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
    return TemplateResponse(request, 'autoplanner/organization.html', context=template_values)


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
def apply_schedule_run(request, schedule_run_pk):
    obj = get_object_or_404(ScheduleRun, pk=schedule_run_pk)
    organization_id = obj.organization_id
    get_object_or_404(Organization.query(request), pk=organization_id)  # only used to check rights
    # required to get the URL of the "administration change page"
    # noinspection PyProtectedMember
    model_admin = admin.site._registry[Organization]
    assert isinstance(model_admin, OrganizationAdmin)
    # noinspection PyProtectedMember
    opts = model_admin.model._meta

    result_dict = json.loads(obj.result_dict)
    end = obj.celery_end
    d = '%(d)s, %(t)s' % {'d': date_format(end, use_l10n=True), 't': time_format(end, use_l10n=True)}
    if not result_dict:
        messages.error(request, _('Unable to apply the invalid schedule "%(d)s".') % {'d': d})
    else:
        try:
            apply_schedule(organization_id, result_dict)
            Organization.objects.filter(pk=organization_id).update(current_schedule=obj.pk)
            ScheduleRun.objects.filter(organization__id=organization_id).exclude(pk=schedule_run_pk)\
                .update(is_selected=False)
            ScheduleRun.objects.filter(pk=schedule_run_pk).update(is_selected=True)
            messages.success(request, _('Schedule "%(d)s" has been applied.') % {'d': d})
        except ValueError as e:
            messages.error(request, _('Unable to apply the invalid schedule "%(d)s": %(e)s.') % {'d': d, 'e': e})

    new_url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                      args=(quote(organization_id),), current_app=model_admin.admin_site.name)
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
        kill_schedule.delay(obj.celery_task_id)
        messages.info(request, _('Computation will be interrupted.') % {'obj': obj})
    new_url = reverse('admin:%s_%s_change' % (opts.app_label, opts.model_name),
                      args=(quote(obj.pk), ), current_app=model_admin.admin_site.name)
    return HttpResponseRedirect(new_url)


@never_cache
def generate_ics(request, organization_pk, agent_pk=None, category_pk=None, title=''):
    obj = get_object_or_404(Organization.query(request, readonly=True), pk=organization_pk)
    cal = Calendar()
    cal.add('prodid', '-//AutoPlanner//19pouces.net//')
    cal.add('version', '2.0')
    cal.add('X-PUBLISHED-TTL', 'PT' + settings.REFRESH_DURATION)
    cal.add('X-WR-TIMEZONE', settings.TIME_ZONE)
    cal.add('X-WR-CALNAME', title or obj.name)
    cal.add('X-WR-CALDESC', obj.description)
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


def index(request):
    query = Organization.query(request).order_by('name')
    set_websocket_topics(request)
    if request.method == 'POST' and request.user.is_authenticated:
        form = OrganizationAddForm(request.POST)
        if form.is_valid():
            obj = Organization(name=form.cleaned_data['name'], max_compute_time=1800)
            obj.save()
            obj.admins.set([request.user])
            messages.success(request, _('Organization successfully created.'))
            return HttpResponseRedirect(reverse('index'))
    else:
        form = OrganizationAddForm()
    template_values = {'organizations': query, 'form': form}
    return TemplateResponse(request, 'autoplanner/organizations.html', context=template_values)


def organization_index(request, organization_pk):
    obj = get_object_or_404(Organization.query(request), pk=organization_pk)
    invalid_tasks = list(Task.objects.filter(organization=obj, end_time__lte=F('start_time')))
    if invalid_tasks:
        if len(invalid_tasks) > 1:
            content = ', '.join([str(x) for x in invalid_tasks])
        else:
            content = str(invalid_tasks[0])
        msg = _('Finish time is before start time for %(t)s') % {'t': content}
        messages.error(request, msg)
    set_websocket_topics(request, obj)
    template_values = {'organization': obj}
    return TemplateResponse(request, 'autoplanner/organization_index.html', context=template_values)
