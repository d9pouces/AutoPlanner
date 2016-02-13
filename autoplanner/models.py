# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.db import models

__author__ = 'Matthieu Gallet'


class Organization(models.Model):
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    time_slice_duration = models.IntegerField('Time slice duration (s)', default=86400)
    time_slice_offset = models.IntegerField('Starting time slice', default=0, blank=True)

    def apply_max_event_affectations(self, agent_pks, events, max_event_affectations_by_category,
                                     parent_categories_per_category, category_pk):
        """ "Agent A cannot execute more than X events of category C in less than T time slices"
        :param agent_pks:
        :type agent_pks:
        :param events:
        :type events:
        :param max_event_affectations_by_category:
        :type max_event_affectations_by_category:
        :param parent_categories_per_category:
        :type parent_categories_per_category:
        :param category_pk:
        :type category_pk:
        """
        durations = {event.pk: (event.end_time_slice - event.start_time_slice) for event in events
                     if category_pk in parent_categories_per_category[event.category_id]}
        event_data = [(event.pk, event.start_time_slice, event.end_time_slice) for event in events
                      if category_pk in parent_categories_per_category[event.category_id]]
        event_data.sort(key=lambda x: (x[1], x[2]))
        previous_start_time_slice = None
        for index, data in enumerate(event_data):
            event_pk, start_time_slice, __ = data
            if start_time_slice == previous_start_time_slice:
                continue
            current_events = {event_pk}
            for max_event_affectation in max_event_affectations_by_category[category_pk]:
                end_block_time_slice = start_time_slice + max_event_affectation.range_time_slice
                event_maximum_duration = max_event_affectation.event_maximum_duration
                for data_2 in event_data[index + 1:]:
                    event_pk_2, start_time_slice_2, __ = data_2
                    if start_time_slice_2 >= end_block_time_slice:
                        break
                    current_events.add(event_pk_2)
                if event_maximum_duration:
                    for agent_pk in agent_pks:
                        variables = ['%d * %s' % (durations[event_pk], self.variable(agent_pk, event_pk))
                                     for event_pk in current_events]
                    yield '%s <= %d' % (' + '.join(variables), max_event_affectation.event_maximum_count)
                else:
                    for agent_pk in agent_pks:
                        variables = [self.variable(agent_pk, event_pk) for event_pk in current_events]
                    yield '%s <= %d' % (' + '.join(variables), max_event_affectation.event_maximum_count)

            previous_start_time_slice = start_time_slice

    def apply_single_event_per_agent(self, agent_pks, events):
        """ "Agent X can perform at most one task at a time"
        :param agent_pks:
        :type agent_pks:
        :param events:
        :type events:
        :return:
        :rtype:
        """
        current_events = set()
        resumed_events = {}
        for event in events:
            resumed_events.setdefault(event.start_time_slice, []).append((event.pk, current_events.add))
            resumed_events.setdefault(event.end_time_slice, []).append((event.pk, current_events.remove))
        time_slices = [x for x in resumed_events]
        time_slices.sort()
        for time_slice in time_slices:
            for (event_pk, action) in time_slices[time_slice]:
                action(event_pk)
            for agent_pk in agent_pks:
                yield '%s <= 1' % ' + '.join([self.variable(agent_pk, event_pk) for event_pk in current_events])

    def balancing_constraints(self, agents, all_category_exclusions, categories, events, preferences,
                              parent_categories_per_category):
        for category in categories:
            category_pk = category.pk
            if category.balancing_mode is None:
                continue
            cat_event_pks = [(event.pk, event.duration) for event in events
                             if category_pk in parent_categories_per_category[event.category_id]]
            cat_agent_pks = []
            for agent in agents:
                agent_pk = agent.pk
                if agent_pk in all_category_exclusions[category_pk]:
                    continue
                agent_preferences = preferences[category_pk].get(agent_pk, (0, 1., 0.))
                if category.balancing_mode == category.BALANCE_NUMBER:
                    ag_sum = ['%g * %s' % (agent_preferences[1], self.variable(agent_pk, x[0])) for x in cat_event_pks]
                else:
                    ag_sum = ['%g * %d * %s' % (agent_preferences[1], x[1], self.variable(agent_pk, x[0]))
                              for x in cat_event_pks]
                yield '%g + %s = %s' % (agent_preferences[0], ag_sum, self.category_variable(category_pk, agent_pk))
                cat_agent_pks.append(agent_pk)
            ag_sum = [self.category_variable(category_pk, agent_pk) for agent_pk in cat_event_pks]
            yield '%s = %s' % (' + '.join(ag_sum), self.category_variable(category_pk))
            for agent_pk in cat_agent_pks:
                yield '%d * %s <= %s + %g' % (len(cat_agent_pks), self.category_variable(category_pk, agent_pk),
                                              self.category_variable(category_pk), category.balancing_tolerance)
                yield '%d * %s >= %s - %g' % (len(cat_agent_pks), self.category_variable(category_pk, agent_pk),
                                              self.category_variable(category_pk), category.balancing_tolerance)

    def affinity_constraints(self, agents, categories, events, preferences, parent_categories_per_category,
                             all_category_exclusions):
        affinity_variables = []
        for category in categories:
            category_pk = category.pk
            if category.balancing_mode is None:
                continue
            cat_event_pks = [(event.pk, event.duration) for event in events
                             if category_pk in parent_categories_per_category[event.category_id]]
            for agent in agents:
                agent_pk = agent.pk
                if agent_pk in all_category_exclusions[category_pk]:
                    continue
                agent_preferences = preferences[category_pk].get(agent_pk, (0, 1., 0.))
                affinity_variables += ['%g * %s' % (agent_preferences[2], self.variable(agent_pk, x[0]))
                                       for x in cat_event_pks if agent_preferences[2]]
        if affinity_variables:
            yield '%s = %s' % (' + '.join(affinity_variables), self.affinity_variable)
        else:
            yield '0 = %s' % self.affinity_variable

    @staticmethod
    def get_agent_preferences(categories, agent_pks, agent_category_preferences, parent_categories_per_category):
        preferences = {a.category_id: {} for a in categories}
        # preferences[category_pk][agent_pk] = (balancing_offset, balancing_count, affinity)
        for a in agent_category_preferences:
            preferences[a.category_id][a.agent_id] = (a.balancing_offset, a.balancing_count, a.affinity)
        for category in categories:
            for agent_pk in agent_pks:
                for parent_pk in parent_categories_per_category[category.pk][1:]:
                    if agent_pk in preferences[parent_pk]:
                        preferences[category.pk][agent_pk] = preferences[parent_pk][agent_pk]
        return preferences

    def get_agent_event_exclusions(self, agents, all_category_exclusions, events, parent_categories_per_category):
        all_agent_event_exclusions = {event.pk: set() for event in events}
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
        for agent_event_exclusion in AgentEventExclusion.objects.filter(organization=self):
            all_agent_event_exclusions[agent_event_exclusion.event_pk].add(agent_event_exclusion.agent_id)
        return all_agent_event_exclusions

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
            if a.balancing_count is None:
                all_category_exclusions[a.category_id].add(a.agent_id)

        all_agent_event_exclusions = self.get_agent_event_exclusions(agents, all_category_exclusions, events,
                                                                     parent_categories_per_category)

        agent_pks = {agent.pk for agent in agents}
        # all events must be done
        available_agents_by_event = {event.pk: (agent_pks - all_agent_event_exclusions[event.pk]) for event in events}
        for event_pk, event_agent_pks in available_agents_by_event.items():
            yield '%s = 1' % ' + '.join([self.variable(agent_pk, event_pk) for agent_pk in event_agent_pks])

        # event with a fixed agent
        for event in events:
            if event.fixed and event.agent_id:
                yield '%s = 1' % self.variable(event.agent_id, event.pk)

        yield from self.apply_single_event_per_agent(agent_pks, events)

        max_event_affectations_by_category = {x.pk: [] for x in categories}
        for max_event_affectation in max_event_affectations:
            max_event_affectations_by_category[max_event_affectation.category_id] = max_event_affectation
        for category in categories:
            category_pk = category.pk
            if not max_event_affectations_by_category[category_pk]:
                continue
            yield from self.apply_max_event_affectations(agent_pks, events, max_event_affectations_by_category,
                                                         parent_categories_per_category, category_pk)
        agent_preferences = self.get_agent_preferences(categories, agent_pks, agent_category_preferences,
                                                       parent_categories_per_category)
        yield from self.balancing_constraints(agents, all_category_exclusions, categories, events, agent_preferences,
                                              parent_categories_per_category)
        yield from self.affinity_constraints(agents, categories, events, agent_preferences,
                                             parent_categories_per_category, all_category_exclusions)
        for event_pk, agent_pks in available_agents_by_event.items():
            for agent_pk in agent_pks:
                yield 'bin %s' % self.variable(agent_pk, event_pk)


    @staticmethod
    def variable(agent_pk, event_pk):
        return 'v_%s_%s' % (agent_pk, event_pk)

    @staticmethod
    def category_variable(category_pk, agent_pk=None):
        if agent_pk is None:
            return 'c_%s' % category_pk
        return 'c_%s_%s' % (category_pk, agent_pk)

    affinity_variable = 'a'


class Agent(models.Model):
    organization = models.ForeignKey(_('Organization'), db_index=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time_slice = models.IntegerField(_('Arrival time slice'), db_index=True, default=0, blank=True)
    end_time_slice = models.IntegerField(_('Leaving time slice'), db_index=True, default=1, blank=True)


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
