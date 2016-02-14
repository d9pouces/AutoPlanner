# -*- coding: utf-8 -*-
from autoplanner.models import Organization

__author__ = 'Matthieu Gallet'


class Constraint(object):
    def __init__(self, value: str, name: str=''):
        self.value = value
        self.name = name


class Scheduler(object):
    def __init__(self, organization: Organization):
        self.organization = organization
        self.agents = {x for x in organization.agent_set.all()}
        self.categories = {x for x in organization.category_set.all()}
        self.max_event_affectations = {x for x in organization.maxeventaffectation_set.all()}
        self.events = {x for x in organization.event_set.all()}
        self.agent_category_preferences = {x for x in organization.agentcategorypreferences_set.all()}

        self.event_durations = {event.pk: (event.end_time_slice - event.start_time_slice) for event in self.events}
        self.agent_pks = {x.pk for x in self.agents}
        # self.agent_pks = {agent1.pk, agent2.pk, agent3.pk}
        self.parent_categories_by_category = self.get_parent_categories_by_category()
        # self.parent_categories_by_category[category.pk] = [category.pk, category.parent.pk, category.parent.parent.pk]
        self.agent_exclusions_by_category = self.get_agent_exclusions_by_category()
        # self.agent_exclusions_by_category[category.pk] = {agent1.pk, agent2.pk, agent3.pk}
        self.agent_exclusions_by_event = self.get_agent_exclusions_by_event()
        # self.agent_exclusions_by_event[event.pk] = {agent1.pk, agent2.pk, agent3.pk}
        self.preferences_by_agent_by_category = self.get_preferences_by_agent_by_category()
        # self.preferences_by_agent_by_category[category.pk][agent.pk] = (balancing_offset, balancing_count, affinity)
        self.max_event_affectations_by_category = self.get_max_event_affectations_by_category()
        # self.max_event_affectations_by_category[category.pk] = [max_event_affectation_1, max_event_affectation_2]
        self.available_agents_by_events = {event.pk: (self.agent_pks - self.agent_exclusions_by_event[event.pk])
                                           for event in self.events}

    def get_parent_categories_by_category(self):
        categories_by_pk = {x.pk: x for x in self.categories}
        parent_categories_per_category = {x.pk: [] for x in self.categories}
        for category in self.categories:
            parent_pk = category.pk
            while parent_pk is not None:
                parent_categories_per_category[category.pk].append(parent_pk)
                parent_pk = categories_by_pk[parent_pk].parent_category_id
        return parent_categories_per_category

    def get_agent_exclusions_by_category(self):
        agent_exclusions_by_category = {category.pk: set() for category in self.categories}
        for a in self.agent_category_preferences:
            if a.balancing_count is None:
                agent_exclusions_by_category[a.category_id].add(a.agent_id)
        return agent_exclusions_by_category

    def get_agent_exclusions_by_event(self):
        agent_event_exclusions = {event.pk: set() for event in self.events}
        for event in self.events:
            event_pk = event.pk
            for category_pk in self.parent_categories_by_category[event.category_id]:
                for agent_pk in self.agent_exclusions_by_category[category_pk]:
                    agent_event_exclusions[event_pk].add(agent_pk)
            for agent in self.agents:
                # TODO optimize
                if agent.start_time_slice > event.start_time_slice:
                    agent_event_exclusions[event_pk].add(agent.pk)
                elif agent.end_time_slice is not None and agent.end_time_slice < event.end_time_slice:
                    agent_event_exclusions[event_pk].add(agent.pk)
        for agent_event_exclusion in self.organization.agenteventexclusion_set.all():
            agent_event_exclusions[agent_event_exclusion.event_pk].add(agent_event_exclusion.agent_id)
        return agent_event_exclusions

    def get_preferences_by_agent_by_category(self):
        preferences = {a.pk: {} for a in self.categories}
        for a in self.agent_category_preferences:
            preferences[a.category_id][a.agent_id] = (a.balancing_offset, a.balancing_count, a.affinity)
        for category in self.categories:
            for agent_pk in self.agent_pks:
                for parent_pk in self.parent_categories_by_category[category.pk][1:]:
                    if agent_pk in preferences[parent_pk]:
                        preferences[category.pk][agent_pk] = preferences[parent_pk][agent_pk]
        return preferences

    def get_max_event_affectations_by_category(self):
        max_event_affectations_by_category = {x.pk: [] for x in self.categories}
        for max_event_affectation in self.max_event_affectations:
            max_event_affectations_by_category[max_event_affectation.category_id].append(max_event_affectation)
        return max_event_affectations_by_category

    def apply_max_event_affectations(self, category_pk: int):
        """ "Agent A cannot execute more than X events of category C in less than T time slices"
        :param category_pk:
        """
        event_data = [(event.pk, event.start_time_slice, event.end_time_slice) for event in self.events
                      if category_pk in self.parent_categories_by_category[event.category_id]]
        event_data.sort(key=lambda x: (x[1], x[2]))
        agent_pks = self.agent_pks - self.agent_exclusions_by_category[category_pk]
        previous_start_time_slice = None
        for index, data in enumerate(event_data):
            event_pk, start_time_slice, __ = data
            if start_time_slice == previous_start_time_slice:
                continue
            current_events = {event_pk}
            for max_event_affectation in self.max_event_affectations_by_category[category_pk]:
                end_block_time_slice = start_time_slice + max_event_affectation.range_time_slice
                event_maximum_duration = max_event_affectation.event_maximum_duration
                for data_2 in event_data[index + 1:]:
                    event_pk_2, start_time_slice_2, __ = data_2
                    if start_time_slice_2 >= end_block_time_slice:
                        break
                    current_events.add(event_pk_2)
                event_maximum_count = max_event_affectation.event_maximum_count
                if event_maximum_duration:
                    for agent_pk in agent_pks:
                        variables = ['%d * %s' % (self.event_durations[event_pk], self.variable(agent_pk, event_pk))
                                     for event_pk in current_events]
                        yield Constraint('%s <= %d' % (' + '.join(variables), event_maximum_count))
                else:
                    for agent_pk in agent_pks:
                        variables = [self.variable(agent_pk, event_pk) for event_pk in current_events]
                        yield Constraint('%s <= %d' % (' + '.join(variables), event_maximum_count))
            previous_start_time_slice = start_time_slice

    def apply_all_events_must_be_done(self):
        """ "Exactly one agent must perform each event"
        """
        for event_pk, event_agent_pks in self.available_agents_by_events.items():
            yield Constraint('%s = 1' % ' + '.join([self.variable(agent_pk, event_pk) for agent_pk in event_agent_pks]))

    def apply_fixed_events(self):
        """ "Event E must be performed by agent A" """
        for event in self.events:
            if event.fixed and event.agent_id:
                yield Constraint('%s = 1' % self.variable(event.agent_id, event.pk))

    def apply_single_event_per_agent(self):
        """ "Agent X can perform at most one task at a time" """
        current_events = set()
        resumed_events = {}
        for event in self.events:
            resumed_events.setdefault(event.start_time_slice, []).append((event.pk, current_events.add))
            resumed_events.setdefault(event.end_time_slice, []).append((event.pk, current_events.remove))
        time_slices = [x for x in resumed_events]
        time_slices.sort()
        for time_slice in time_slices:
            for (event_pk, action) in resumed_events[time_slice]:
                action(event_pk)
            if not current_events:
                continue
            for agent_pk in self.agent_pks:
                variables = [self.variable(agent_pk, event_pk) for event_pk in current_events]
                yield Constraint('%s <= 1' % ' + '.join(variables))

    def apply_balancing_constraints(self):
        for category in self.categories:
            if category.balancing_mode is None:
                continue
            category_pk = category.pk
            cat_event_pks = [event.pk for event in self.events
                             if category_pk in self.parent_categories_by_category[event.category_id]]
            cat_agent_pks = self.agent_pks - self.agent_exclusions_by_category[category_pk]
            for agent in cat_agent_pks:
                agent_pk = agent.pk
                agent_preferences = self.preferences_by_agent_by_category[category_pk].get(agent_pk, (0, 1., 0.))
                if category.balancing_mode == category.BALANCE_NUMBER:
                    ag_sum = ['%g * %s' % (agent_preferences[1], self.variable(agent_pk, event_pk))
                              for event_pk in cat_event_pks]
                else:
                    ag_sum = ['%g * %d * %s' % (agent_preferences[1], self.event_durations[event_pk],
                                                self.variable(agent_pk, event_pk)) for event_pk in cat_event_pks]
                yield Constraint('%g + %s = %s' % (agent_preferences[0], ' + '.join(ag_sum),
                                                   self.category_variable(category_pk, agent_pk)))
            ag_sum = [self.category_variable(category_pk, agent_pk) for agent_pk in cat_agent_pks]
            yield Constraint('%s = %s' % (' + '.join(ag_sum), self.category_variable(category_pk)))
            for agent_pk in cat_agent_pks:
                yield Constraint(
                    '%d * %s <= %s + %g' % (len(cat_agent_pks), self.category_variable(category_pk, agent_pk),
                                            self.category_variable(category_pk), category.balancing_tolerance))
                yield Constraint(
                    '%d * %s >= %s - %g' % (len(cat_agent_pks), self.category_variable(category_pk, agent_pk),
                                            self.category_variable(category_pk), category.balancing_tolerance)
                )

    def apply_affinity_constraints(self):
        variables = []
        for category in self.categories:
            category_pk = category.pk
            cat_event_pks = [(event.pk, event.start_time_slice, event.end_time_slice) for event in self.events
                             if category_pk in self.parent_categories_by_category[event.category_id]]
            # if category.auto_affinity:
            # cat_event_pks.sort(key=lambda x: x[1])
            for agent_pk in self.agent_pks - self.agent_exclusions_by_category[category_pk]:
                agent_preferences = self.preferences_by_agent_by_category[category_pk].get(agent_pk, (0, 1., 0.))
                variables += ['%g * %s' % (agent_preferences[2], self.variable(agent_pk, x[0]))
                              for x in cat_event_pks if agent_preferences[2]]
        if variables:
            yield Constraint('%s = %s' % (' + '.join(variables), self.affinity_variable()))
        else:
            yield Constraint('0 = %s' % self.affinity_variable())

    def constraints(self):
        # all events must be done
        yield from self.apply_all_events_must_be_done()
        # event with a fixed agent
        yield from self.apply_fixed_events()
        # at most one event by agent at the same time
        yield from self.apply_single_event_per_agent()
        for category in self.categories:
            if self.max_event_affectations_by_category[category.pk]:
                yield from self.apply_max_event_affectations(category.pk)
        yield from self.apply_balancing_constraints()
        yield from self.apply_affinity_constraints()
        for event_pk, agent_pks in self.available_agents_by_events.items():
            for agent_pk in agent_pks:
                yield Constraint('bin %s' % self.variable(agent_pk, event_pk))

    @staticmethod
    def variable(agent_pk, event_pk):
        return 'v_a%s_e%s' % (agent_pk, event_pk)

    @staticmethod
    def category_variable(category_pk, agent_pk=None):
        if agent_pk is None:
            return 'c_c%s' % category_pk
        return 'c_c%s_a%s' % (category_pk, agent_pk)

    @staticmethod
    def affinity_variable():
        return 'a'

