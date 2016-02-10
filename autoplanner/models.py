# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.db import models

__author__ = 'Matthieu Gallet'


class Organization(models.Model):
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    time_slice_duration = models.IntegerField('Time slice duration (s)', default=86400)
    time_slice_offset = models.IntegerField('Starting time slice', default=0, blank=True)


class Agent(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Arrival time slice'), db_index=True, default=0, blank=True)
    end_time_slice = models.IntegerField(_('Leaving time slice'), db_index=True, default=None, blank=True, null=True)


class Category(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    parent_category = models.ForeignKey('self', db_index=True, null=True, blank=True, default=None,
                                        verbose_name=_('Parent category'))
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    min_spacing = models.IntegerField(_('Minimum number of time units between successive events for a given person'),
                                      default=0, blank=True)
    balancing_tolerance = models.FloatField(_('Tolerance for balancing the total duration across agents'),
                                            default=None, null=True, blank=True,
                                            help_text=_('Leave it blank to avoid balancing'))
    max_contiguous_tolerance = models.FloatField(_('Tolerance for respecting the max number of successive events'),
                                                 blank=True, default=0.)
    auto_affinity = models.FloatField(_('Affinity for allocating events of the same category to the same agent'),
                                      default=0., blank=True)


class MaxEventAffectation(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    range_time_slice = models.IntegerField(_('Period length (in time units)'), default=2)
    event_maximum_count = models.IntegerField(_('Maximum number of events in this range'), default=1)


class Event(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Start time'), db_index=True)
    end_time_slice = models.IntegerField(_('End time'), db_index=True)
    agent = models.ForeignKey(Agent, db_index=True, null=True, default=None, blank=True)
    fixed = models.BooleanField(_('Agent is strongly fixed'), db_index=True, default=False)


class AgentCategoryPreferences(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    affinity = models.FloatField(_('Affinity of the agent for the category.'), default=0., blank=True)
    balancing_offset = models.FloatField(_('Number of events already done'), default=0, blank=True)
    balancing_count = models.FloatField(_('If an agent should perform less events of this category,'
                                          'it should be > 1.0'), default=1.0, blank=True, null=True,
                                        help_text=_('Blank if the agent cannot perform events of this category'))


class AgentEventExclusion(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    agent = models.ForeignKey(Agent, db_index=True)
    event = models.ForeignKey(Event, db_index=True)
