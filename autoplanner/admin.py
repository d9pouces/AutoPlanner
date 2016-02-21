# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.sites.models import Site
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Task, AgentCategoryPreferences, AgentTaskExclusion, MaxTaskAffectation, Category, \
    Agent, Organization, MaxTimeTaskAffectation


__author__ = 'Matthieu Gallet'


class AgentInline(admin.TabularInline):
    model = Agent
    show_change_link = True
    classes = ['collapse', 'collapsed']


class CategoryInline(admin.TabularInline):
    model = Category
    classes = ['collapse', 'collapsed']

    def get_extra(self, request, obj=None, **kwargs):
        if request.GET.get('readonly'):
            return 0
        elif obj and obj.category_set.all().count() > 3:
            return 1
        return 3

    def get_readonly_fields(self, request, obj=None):
        if request.GET.get('readonly'):
            return ['parent_category', 'name', 'balancing_mode', 'balancing_tolerance', 'auto_affinity']
        return []


class TaskInline(admin.TabularInline):
    model = Task
    classes = ['collapse', 'collapsed']

    @staticmethod
    def repeat_button(obj):
        if obj and obj.pk:
            return format_html('<a href="{}" class="button default">{}</a>',
                               reverse('multiply_task', kwargs={'task_pk': obj.pk}),
                               _('Repeat'))
        return ''

    repeat_button.allow_tags = True
    repeat_button.verbose_name = _('Repeat')
    readonly_fields = ('repeat_button', )
    fields = ('category', 'name', 'start_time', 'end_time', 'agent', 'fixed', 'repeat_button')

    def get_readonly_fields(self, request, obj=None):
        if request.GET.get('readonly'):
            return ['category', 'name', 'start_time', 'end_time', 'agent', 'fixed', 'repeat_button', ]
        return ['repeat_button', ]

    def get_extra(self, request, obj=None, **kwargs):
        if request.GET.get('readonly'):
            return 0
        return 3


class MaxTaskAffectationInline(admin.TabularInline):
    model = MaxTaskAffectation
    classes = ['collapse', 'collapsed']


class MaxTimeTaskAffectationInline(admin.TabularInline):
    model = MaxTimeTaskAffectation
    classes = ['collapse', 'collapsed']


class OrganizationAdmin(admin.ModelAdmin):
    exclude = ['message', 'celery_task_id', 'celery_start', 'celery_end']

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = get_object_or_404(Organization, pk=object_id)
        if obj.message:
            messages.info(request, obj.message)
        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

    # noinspection PyMethodMayBeStatic
    def schedule_button(self, obj):
        if obj and obj.pk:
            if not obj.celery_task_id:
                return format_html('<a href="{}" class="button default">{}</a>',
                                   reverse('schedule_start', kwargs={'organization_pk': obj.pk}),
                                   _('Schedule it!'))
            else:
                return format_html('<a href="{}" class="button default">{}</a>',
                                   reverse('cancel_schedule', kwargs={'organization_pk': obj.pk}),
                                   _('Cancel the schedule'))
        return ''

    schedule_button.allow_tags = True
    schedule_button.short_description = _('Compute a complete schedule')
    readonly_fields = ('schedule_button', )
    fields = ['name', 'description', 'schedule_button', ]
    inlines = [AgentInline, CategoryInline, MaxTaskAffectationInline, MaxTimeTaskAffectationInline, TaskInline, ]


class AgentCategoryPreferencesInline(admin.StackedInline):
    model = AgentCategoryPreferences
    fields = ('category', 'agent', 'affinity', 'balancing_offset', 'balancing_count', )
    classes = ['collapse', 'collapsed']


class AgentTaskExclusionInline(admin.TabularInline):
    model = AgentTaskExclusion
    fields = ('agent', 'task', )


class AgentAdmin(admin.ModelAdmin):
    inlines = [AgentCategoryPreferencesInline, AgentTaskExclusionInline]

    def get_fields(self, request, obj=None):
        fields = ['name', 'start_time', 'end_time']
        if obj is None:
            fields = ['organization'] + fields
        return fields


class TaskAdmin(admin.ModelAdmin):

    # noinspection PyMethodMayBeStatic
    def repeat_button(self, obj):
        if obj and obj.pk:
            return format_html('<a href="{}" class="button default">{}</a>',
                               reverse('multiply_task', kwargs={'task_pk': obj.pk}),
                               _('Repeat'))
        return ''

    repeat_button.allow_tags = True
    readonly_fields = ('repeat_button', )
    repeat_button.short_description = _('Repeat')

    fields = ['category', 'name', 'start_time', 'end_time', 'agent', 'fixed', ]
    list_display = ['name', 'category', 'start_time', 'end_time', 'agent', 'fixed', 'repeat_button', ]
    list_editable = ['category', 'start_time', 'end_time', 'agent', 'fixed']
    list_filter = ['category', 'agent', 'organization', 'fixed', ]


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.unregister(Site)
admin.site.site_header = _('AutoPlanner')