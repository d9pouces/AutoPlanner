# -*- coding: utf-8 -*-
from autoplanner.models import Organization, Agent, Category, MaxEventAffectation, Event, AgentCategoryPreferences, \
    AgentEventExclusion

__author__ = 'Matthieu Gallet'


class Scheduler(object):
    def get_agent_exclusions_by_category(self):
        agent_exclusions_by_category = {category.pk: set() for category in self.categories}
        for a in self.agent_category_preferences:
            if a.balancing_count is None:
                agent_exclusions_by_category[a.category_id].add(a.agent_id)
        return agent_exclusions_by_category

    def __init__(self, organization: Organization):
        self.organization = organization
        self.agents = {x for x in organization.agent_set.all()}
        self.categories = {x for x in organization.category_set.all()}
        self.max_event_affectations = {x for x in organization.maxeventaffectation_set.all()}
        self.events = {x for x in organization.event_set.all()}
        self.agent_category_preferences = {x for x in organization.agentcategorypreferences_set.all()}

        categories_by_pk = {x.pk: x for x in self.categories}
        self.parent_categories_per_category = {x.pk: [] for x in self.categories}
        for category in self.categories:
            parent_pk = category.pk
            while parent_pk is not None:
                self.parent_categories_per_category[category.pk].append(parent_pk)
                parent_pk = categories_by_pk[parent_pk].parent_category_id
        self.agent_exclusions_by_category = self.get_agent_exclusions_by_category()
        self.agent_exclusions_by_event = self.get_agent_exclusions_by_event()

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
            for (event_pk, action) in resumed_events[time_slice]:
                action(event_pk)
            if not current_events:
                continue
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
                yield '%g + %s = %s' % (agent_preferences[0], ' + '.join(ag_sum), self.category_variable(category_pk, agent_pk))
                cat_agent_pks.append(agent_pk)
            ag_sum = [self.category_variable(category_pk, agent_pk) for agent_pk in cat_agent_pks]
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
            cat_event_pks = [(event.pk, event.start_time_slice, event.end_time_slice) for event in events
                             if category_pk in parent_categories_per_category[event.category_id]]
            # if category.auto_affinity:
            #     cat_event_pks.sort(key=lambda x: x[1])
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
        preferences = {a.pk: {} for a in categories}
        # preferences[category_pk][agent_pk] = (balancing_offset, balancing_count, affinity)
        for a in agent_category_preferences:
            preferences[a.category_id][a.agent_id] = (a.balancing_offset, a.balancing_count, a.affinity)
        for category in categories:
            for agent_pk in agent_pks:
                for parent_pk in parent_categories_per_category[category.pk][1:]:
                    if agent_pk in preferences[parent_pk]:
                        preferences[category.pk][agent_pk] = preferences[parent_pk][agent_pk]
        return preferences

    def get_agent_exclusions_by_event(self, agents, events, parent_categories_per_category):
        agent_event_exclusions = {event.pk: set() for event in events}
        for event in events:
            event_pk = event.pk
            for category_pk in parent_categories_per_category[event.category_id]:
                for agent_pk in self.agent_exclusions_by_category[category_pk]:
                    agent_event_exclusions[event_pk].add(agent_pk)
            for agent in agents:
                if agent.start_time_slice > event.start_time_slice:
                    agent_event_exclusions[event_pk].add(agent.pk)
                elif agent.end_time_slice is not None and agent.end_time_slice < event.end_time_slice:
                    agent_event_exclusions[event_pk].add(agent.pk)
        for agent_event_exclusion in AgentEventExclusion.objects.filter(organization=self):
            agent_event_exclusions[agent_event_exclusion.event_pk].add(agent_event_exclusion.agent_id)
        return agent_event_exclusions

    def constraints(self):
        all_agent_event_exclusions = self.get_agent_exclusions_by_event(agents, all_category_exclusions, events,
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
        return 'v_a%s_e%s' % (agent_pk, event_pk)

    @staticmethod
    def category_variable(category_pk, agent_pk=None):
        if agent_pk is None:
            return 'c_c%s' % category_pk
        return 'c_c%s_a%s' % (category_pk, agent_pk)

    affinity_variable = 'a'
