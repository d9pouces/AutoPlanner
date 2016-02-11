# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.db import models

__author__ = 'Matthieu Gallet'


class Organization(models.Model):
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    time_slice_duration = models.IntegerField('Time slice duration (s)', default=86400)
    time_slice_offset = models.IntegerField('Starting time slice', default=0, blank=True)

    def constraints(self):
        agents = {x for x in Agent.objects.filter(organization=self)}
        categories = {x for x in Category.objects.filter(organization=self)}
        max_event_affectations = {x for x in MaxEventAffectation.objects.filter(organization=self)}
        events = {x for x in Event.objects.filter(organization=self)}
        agent_category_preferences = {x for x in AgentCategoryPreferences.objects.filter(organization=self)}

        categories_by_pk = {x.pk: x for x in categories}
        parent_categories_per_category = {x.pk: [] for x in categories}
        for category in categories:
            parent_pk = category.pk
            while parent_pk is not None:
                parent_categories_per_category[category.pk].append(parent_pk)
                parent_pk = categories_by_pk[parent_pk].parent_id

        all_category_exclusions = {category.pk: set() for category in categories}
        for a in agent_category_preferences:
            all_category_exclusions[a.category_id].add(a.agent_id)

        all_agent_event_exclusions = {event.pk: set() for event in events}
        min_time_slice, max_time_slice = None, None
        for event in events:
            event_pk = event.pk
            for category_pk in parent_categories_per_category[event.category_id]:
                for agent_pk in all_category_exclusions[category_pk]:
                    all_agent_event_exclusions[event_pk].add(agent_pk)
            for agent in agents:
                if agent.start_time_slice > event.start_time_slice:
                    all_agent_event_exclusions[event_pk].add(agent.pk)
                elif agent.end_time_slice is not None and agent.end_time_slice < event.end_time_slice:
                    all_agent_event_exclusions[event_pk].add(agent.pk)
            if min_time_slice is None or min_time_slice > event.start_time_slice:
                min_time_slice = event.start_time_slice
            if max_time_slice is None or max_time_slice > event.end_time_slice:
                max_time_slice = event.end_time_slice
        for agent_event_exclusion in AgentEventExclusion.objects.filter(organization=self):
            all_agent_event_exclusions[agent_event_exclusion.event_pk].add(agent_event_exclusion.agent_id)

        agent_pks = {agent.pk for agent in agents}
        available_agents_by_event = {event.pk: (agent_pks - all_agent_event_exclusions[event.pk]) for event in events}
        for event_pk, agent_pks in available_agents_by_event.items():
            yield '%s = 1' % ' + '.join([self.variable(agent_pk, event_pk) for agent_pk in agent_pks])

        events_by_timeslices = {}
        for event in events:
            for time_slice in range(event.start_time_slice, event.end_time_slice + 1):
                events_by_timeslices.setdefault(time_slice, set()).add(event.pk)
            if event.agent_id and event.fixed:
                yield '%s = 1' % self.variable(event.agent_id, event.pk)
        constraints = set()
        for time_slice, event_pks in events_by_timeslices.items():
            for agent_pk in agent_pks:
                variables = [self.variable(agent_pk, event_pk) for event_pk in event_pks
                             if agent_pk in available_agents_by_event[event_pk]]
                if not variables:
                    continue
                constraint = '%s <= 1' % ' + '.join(variables)
                if constraint not in constraints:
                    yield constraint
                    constraints.add(constraint)

        max_event_affectations_by_category = {x.pk: [] for x in categories}
        for max_event_affectation in max_event_affectations:
            max_event_affectations_by_category[max_event_affectation.category_id] = max_event_affectation
        for category in categories:
            category_pk = category.pk
            if not max_event_affectations_by_category[category_pk]:
                continue
            events = [(event.pk, event.start_time_slice, event.end_time_slice) for event in events
                      if category_pk in parent_categories_per_category[event.category_id]]
            events.sort(key=lambda x: x[1])
            current_events = {}  # current_events[end_time_slice] = [event_pk1, event_pk2]
            for event_pk, start_time_slice, end_time_slice in events:
                pass

        for event_pk, agent_pks in available_agents_by_event.items():
            for agent_pk in agent_pks:
                yield 'bin %s' % self.variable(agent_pk, event_pk)

    @staticmethod
    def variable(agent_pk, event_pk):
        return 'v_%s_%s' % (agent_pk, event_pk)


class Agent(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Arrival time slice'), db_index=True, default=0, blank=True)
    end_time_slice = models.IntegerField(_('Leaving time slice'), db_index=True, default=1, blank=True)


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
    auto_affinity = models.FloatField(_('Affinity for allocating successive events of the same category '
                                        'to the same agent'),
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
    end_time_slice = models.IntegerField(_('End time'), db_index=True, default=None, blank=True, null=True)
    agent = models.ForeignKey(Agent, db_index=True, null=True, default=None, blank=True)
    fixed = models.BooleanField(_('Agent is strongly fixed'), db_index=True, default=False)

    @property
    def duration(self):
        return self.end_time_slice - self.start_time_slice


class AgentCategoryPreferences(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    category = models.ForeignKey(Category, db_index=True)
    affinity = models.FloatField(_('Affinity of the agent for the category.'), default=0., blank=True)
    balancing_offset = models.FloatField(_('Number of time units already done'), default=0, blank=True)
    balancing_count = models.FloatField(_('If an agent should perform less events of this category,'
                                          'it should be > 1.0'), default=1.0, blank=True, null=True,
                                        help_text=_('Blank if the agent cannot perform events of this category'))


class AgentEventExclusion(models.Model):
    organization = models.ForeignKey(Organization, db_index=True)
    agent = models.ForeignKey(Agent, db_index=True)
    event = models.ForeignKey(Event, db_index=True)
