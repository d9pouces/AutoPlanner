# -*- coding: utf-8 -*-
from django.contrib import admin
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Task, AgentCategoryPreferences, AgentTaskExclusion, MaxTaskAffectation, Category, \
    Agent, Organization, MaxTimeTaskAffectation


__author__ = 'Matthieu Gallet'


class AgentInline(admin.TabularInline):
    model = Agent


class CategoryInline(admin.TabularInline):
    model = Category

    def get_extra(self, request, obj=None, **kwargs):
        if obj.category_set.all().count() > 3:
            return 1
        return 3


class TaskInline(admin.TabularInline):
    model = Task


class MaxTaskAffectationInline(admin.TabularInline):
    model = MaxTaskAffectation


class MaxTimeTaskAffectationInline(admin.TabularInline):
    model = MaxTimeTaskAffectation


class OrganizationAdmin(admin.ModelAdmin):
    inlines = [AgentInline, CategoryInline, TaskInline, MaxTaskAffectationInline, MaxTimeTaskAffectationInline]


class AgentCategoryPreferencesInline(admin.StackedInline):
    model = AgentCategoryPreferences
    fields = ('category', 'agent', 'affinity', 'balancing_offset', 'balancing_count', )


class AgentTaskExclusionInline(admin.TabularInline):
    model = AgentTaskExclusion
    fields = ('agent', 'task', )


class AgentAdmin(admin.ModelAdmin):
    inlines = [AgentCategoryPreferencesInline, AgentTaskExclusionInline]

    def get_fields(self, request, obj=None):
        fields = ['name', 'start_time_slice', 'end_time_slice']
        if obj is None:
            fields = ['organization'] + fields
        return fields


class TaskAdmin(admin.ModelAdmin):

    fields = ['category', 'name', 'start_time_slice', 'end_time_slice', 'agent', 'fixed',]
    list_display = [str, 'category', 'start_time_slice', 'end_time_slice', 'agent', 'fixed']
    list_editable = ['category', 'start_time_slice', 'end_time_slice', 'agent', 'fixed']


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Agent, AgentAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.unregister(Site)
admin.site.site_header = _('AutoPlanner')