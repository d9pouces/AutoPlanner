# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Task, AgentCategoryPreferences, AgentTaskExclusion, MaxTaskAffectation, Category, \
    Agent, Organization, MaxTimeTaskAffectation, ScheduleRun

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
            return ['name', 'balancing_mode', 'balancing_tolerance', 'auto_affinity']
        return []


class TaskInline(admin.TabularInline):
    model = Task
    classes = ['collapse', 'collapsed']

    @staticmethod
    def repeat(obj):
        if obj and obj.pk:
            return format_html('<a href="{}" class="button default">{}</a>',
                               reverse('multiply_task', kwargs={'task_pk': obj.pk}),
                               _('Repeat'))
        return ''

    repeat.allow_tags = True
    repeat.verbose_name = _('Repeat')
    readonly_fields = ('repeat',)
    fields = ('categories', 'name', 'start_time', 'end_time', 'agent', 'fixed', 'repeat')

    def get_readonly_fields(self, request, obj=None):
        if request.GET.get('readonly'):
            return ['categories', 'name', 'start_time', 'end_time', 'agent', 'fixed', 'repeat', ]
        return ['repeat', ]

    def get_extra(self, request, obj=None, **kwargs):
        if request.GET.get('readonly'):
            return 0
        return 3


class MaxTaskAffectationInline(admin.TabularInline):
    model = MaxTaskAffectation
    classes = ['collapse', 'collapsed']


class ScheduleRunInline(admin.TabularInline):
    model = ScheduleRun
    classes = ['collapse', 'collapsed']

    @staticmethod
    def apply(obj):
        if obj and obj.pk and obj.status:
            if obj.is_selected:
                return format_html('<span class="button default" style="background-color: #0B6138;">{}</span>',
                                   _('Current schedule'))
            return format_html('<a href="{}" class="button default">{}</a>',
                               reverse('apply_schedule_run', kwargs={'schedule_run_pk': obj.pk}),
                               _('Select this schedule'))
        return ''
    extra = 0
    apply.allow_tags = True
    apply.verbose_name = _('Reload this schedule')
    readonly_fields = ['status', 'message', 'celery_start', 'celery_end', 'apply']
    fields = ['status', 'message', 'celery_start', 'celery_end', 'apply']

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class MaxTimeTaskAffectationInline(admin.TabularInline):
    model = MaxTimeTaskAffectation
    classes = ['collapse', 'collapsed']


class OrganizationAdmin(admin.ModelAdmin):
    exclude = ['message', 'celery_task_id', 'celery_start', 'celery_end']
    list_display = ['name', 'message', 'access_token']

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = get_object_or_404(Organization, pk=object_id)
        if obj.message and request.method == 'GET':
            messages.info(request, obj.message)
        return super().change_view(request, object_id, form_url=form_url, extra_context=extra_context)

    # noinspection PyMethodMayBeStatic
    def schedule_button(self, obj):
        if obj and obj.pk:
            if not obj.celery_task_id:
                return format_html('<a href="{}" class="button default">{}</a>',
                                   reverse('schedule_start', kwargs={'organization_pk': obj.pk}),
                                   _('Compute a new schedule!'))
            else:
                return format_html('<a href="{}" class="button default">{}</a>',
                                   reverse('cancel_schedule', kwargs={'organization_pk': obj.pk}),
                                   _('Cancel the currently running schedule'))
        return ''

    def get_queryset(self, request):
        return self.model.query(request)

    schedule_button.allow_tags = True
    schedule_button.short_description = _('Compute a complete schedule')
    readonly_fields = ('schedule_button',)
    fields = ['name', 'description', 'access_token', 'admins', 'schedule_button', 'max_compute_time', ]
    inlines = [ScheduleRunInline, AgentInline, CategoryInline, MaxTaskAffectationInline, MaxTimeTaskAffectationInline,
               TaskInline, ]


class AgentCategoryPreferencesInline(admin.StackedInline):
    model = AgentCategoryPreferences
    fields = ('category', 'agent', 'affinity', 'balancing_offset', 'balancing_count',)
    classes = ['collapse', 'collapsed']


class AgentTaskExclusionInline(admin.TabularInline):
    model = AgentTaskExclusion
    fields = ('agent', 'task',)


class AgentAdmin(admin.ModelAdmin):
    inlines = [AgentCategoryPreferencesInline, AgentTaskExclusionInline]
    list_display = ('name', 'organization', 'start_time', 'end_time',)
    list_filter = ('organization',)

    def get_queryset(self, request):
        return self.model.query(request)

    def get_fields(self, request, obj=None):
        fields = ['name', 'start_time', 'end_time']
        if obj is None:
            fields = ['organization'] + fields
        return fields


class TaskAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.query(request)

    # noinspection PyMethodMayBeStatic
    def repeat_button(self, obj):
        if obj and obj.pk:
            return format_html('<a href="{}" class="button default">{}</a>',
                               reverse('multiply_task', kwargs={'task_pk': obj.pk}),
                               _('Repeat'))
        return ''

    def fix_agents(self, request, queryset):
        rows_updated = queryset.exclude(agent=None).update(fixed=True)
        if rows_updated > 1:
            self.message_user(request, _('%(t)s tasks have been updated') % {'t': rows_updated})
        else:
            self.message_user(request, _('%(t)s task has been updated') % {'t': rows_updated})

    fix_agents.short_description = _('Fix the agent processing the selected tasks ')

    def unfix_agents(self, request, queryset):
        rows_updated = queryset.exclude(agent=None).update(fixed=False)
        if rows_updated > 1:
            self.message_user(request, _('%(t)s tasks have been updated') % {'t': rows_updated})
        else:
            self.message_user(request, _('%(t)s task has been updated') % {'t': rows_updated})

    unfix_agents.short_description = _('Unfix the agent processing the selected tasks ')

    repeat_button.allow_tags = True
    readonly_fields = ('repeat_button',)
    repeat_button.short_description = _('Repeat')
    actions = ['fix_agents', 'unfix_agents']
    search_fields = ['name', ]
    fields = ['categories', 'name', 'start_time', 'end_time', 'agent', 'fixed', ]
    list_display = ['name', 'start_time', 'end_time', 'agent', 'fixed', 'repeat_button', ]
    list_editable = ['start_time', 'end_time', 'agent', 'fixed']
    list_filter = ['categories', 'agent', 'organization', 'fixed', 'start_time', 'end_time', ]


class AgentCategoryPreferencesAdmin(admin.ModelAdmin):
    list_display = ['category', 'agent', 'affinity', 'balancing_offset', 'balancing_count']
    list_filter = ['category', 'agent', 'organization', ]


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(AgentCategoryPreferences, AgentCategoryPreferencesAdmin)
# admin.site.unregister(Site)
admin.site.site_header = _('AutoPlanner')
