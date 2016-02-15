# -*- coding: utf-8 -*-
import datetime
from django.http import HttpRequest
from django.utils.timezone import utc

from django.utils.translation import ugettext as _
from django.db import models

YEAR_0 = datetime.datetime(1970, 1, 1, tzinfo=utc)

__author__ = 'Matthieu Gallet'


class Organization(models.Model):
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    time_slice_duration = models.IntegerField('Time slice duration (s)', default=3600)
    time_slice_offset = models.IntegerField('Starting time slice', default=0, blank=True)

    # noinspection PyUnusedLocal
    @classmethod
    def query(cls, request: HttpRequest):
        return cls.objects.all()

    def __str__(self):
        return self.name

    def get_time(self, time_slice: int) -> datetime.datetime:
        return YEAR_0 + datetime.timedelta(seconds=time_slice * self.time_slice_duration) + \
            datetime.timedelta(seconds=self.time_slice_offset)

    def from_time(self, time: datetime.datetime) -> int:
        delta = (time - YEAR_0 - datetime.timedelta(seconds=self.time_slice_offset))
        return int(delta.total_seconds() / self.time_slice_duration)


class Agent(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Arrival time slice'), db_index=True, default=0, blank=True)
    end_time_slice = models.IntegerField(_('Leaving time slice'), db_index=True, default=None, blank=True, null=True)


class Category(models.Model):
    BALANCE_TIME = 'time'
    BALANCE_NUMBER = 'number'
    organization = models.ForeignKey(_('Organization'), db_index=True)
    parent_category = models.ForeignKey('self', db_index=True, null=True, blank=True, default=None,
                                        verbose_name=_('Parent category'))
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    balancing_mode = models.CharField(_('Balancing mode'),
                                      max_length=10, choices=((None, _('No balancing')),
                                                              (BALANCE_TIME, _('Total event time')),
                                                              (BALANCE_NUMBER, _('Total event number'))),
                                      blank=True, null=True, default=None)
    balancing_tolerance = models.FloatField(_('Tolerance for balancing the total duration across agents'),
                                            default=1., blank=True)
    auto_affinity = models.FloatField(_('Affinity for allocating successive events of the same category '
                                        'to the same agent'), default=0., blank=True)

    def __str__(self):
        return self.name


class MaxEventAffectation(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    range_time_slice = models.IntegerField(_('Period length (in time units)'), default=2)
    event_maximum_count = models.IntegerField(_('Maximum number of events in this range'), default=1)
    event_maximum_duration = models.BooleanField(_('Use event durations'), default=False)


class Event(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Start time'), db_index=True)
    end_time_slice = models.IntegerField(_('End time'), db_index=True, default=None, blank=True, null=True)
    agent = models.ForeignKey(Agent, db_index=True, null=True, default=None, blank=True)
    fixed = models.BooleanField(_('Agent is strongly fixed'), db_index=True, default=False)

    @property
    def duration(self):
        return self.end_time_slice - self.start_time_slice

    def __str__(self):
        return self.name


class AgentCategoryPreferences(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    agent = models.ForeignKey(Agent, db_index=True)
    affinity = models.FloatField(_('Affinity of the agent for the category.'), default=0., blank=True)
    balancing_offset = models.FloatField(_('Number of time units already done'), default=0, blank=True)
    balancing_count = models.FloatField(_('If an agent should perform less events of this category,'
                                          'it should be > 1.0'), default=1.0, blank=True, null=True,
                                        help_text=_('Blank if the agent cannot perform events of this category'))


class AgentEventExclusion(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    agent = models.ForeignKey(Agent, db_index=True)
    event = models.ForeignKey(Event, db_index=True)
