# -*- coding: utf-8 -*-
from django.contrib import admin

from autoplanner.models import Event, AgentCategoryPreferences, AgentEventExclusion, MaxEventAffectation, Category, \
    Agent, Organization


__author__ = 'Matthieu Gallet'


class AgentInline(admin.TabularInline):
    model = Agent


class CategoryInline(admin.TabularInline):
    model = Category


class EventInline(admin.TabularInline):
    model = Event


class MaxEventAffectationInline(admin.TabularInline):
    model = MaxEventAffectation


class OrganizationAdmin(admin.ModelAdmin):
    inlines = [AgentInline, CategoryInline, EventInline, MaxEventAffectationInline]


class AgentCategoryPreferencesInline(admin.TabularInline):
    model = AgentCategoryPreferences


class AgentEventExclusionInline(admin.TabularInline):
    model = AgentEventExclusion


class AgentAdmin(admin.ModelAdmin):
    inlines = [AgentCategoryPreferencesInline, AgentEventExclusionInline]


admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Agent, AgentAdmin)
