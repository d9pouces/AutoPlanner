# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.db import models
__author__ = 'Matthieu Gallet'


class Organization(models.Model):
    HALF_DAY = 'half_day'
    DAY = 'day'
    WEEK = 'week'
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    unit = models.IntegerField('Time slice duration (s)', default=86400)
    offset_time_slice = models.IntegerField('Starting time slice', default=0, blank=True)


class Agent(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Arrival time slice'), db_index=True, default=0, blank=True)
    end_time_slice = models.IntegerField(_('Leaving time slice'), db_index=True, default=None, blank=True, null=True)


class EventCategory(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    max_contiguous_events = models.IntegerField(_('Maximum successive events for a given person'),
                                                default=0, blank=True, )


class Event(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(EventCategory, db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Start time'), db_index=True)
    end_time_slice = models.IntegerField(_('End time'), db_index=True)
    agent = models.ForeignKey(Agent, db_index=True, null=True, default=None, blank=True)
    fixed = models.BooleanField(_('Is strongly fixed'), db_index=True, default=False)


class AgentEventAffinity(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(EventCategory, db_index=True)
    affinity = models.FloatField(_('Affinity of the agent for the category.'), default=1., blank=True, null=True,
                                 help_text=_('Leave it blank if the agent cannot perform events of this category'))
    balancing_offset = models.FloatField(_('Number of events already done'), default=0, blank=True)
    balancing_count = models.FloatField(_('If an agent should perform less events of this category,'
                                          'it should be > 1.0'), default=1.0, blank=True)
