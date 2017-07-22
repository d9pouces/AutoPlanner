# -*- coding: utf-8 -*-
import re
import subprocess
import tempfile
from django.conf import settings

from autoplanner.models import Organization, MaxTimeTaskAffectation, Task, ScheduleRun

__author__ = 'Matthieu Gallet'


class Constraint(object):
    def __init__(self, value: str, name: str=''):
        self.value = value
        self.name = name

    def __str__(self):
        return self.value


class Scheduler(object):
    def __init__(self, organization: Organization):
        self.organization = organization
        self.agents = {x for x in organization.agent_set.all()}
        self.categories = {x for x in organization.category_set.all()}
        self.categories_by_pk = {x.pk: x for x in self.categories}
        self.tasks = {x for x in organization.task_set.all() if (x.start_time < x.end_time)}
        self.agent_category_preferences = {x for x in organization.agentcategorypreferences_set.all()}

        self.task_durations = {task.pk: (task.end_time - task.start_time).total_seconds()
                               for task in self.tasks}
        self.agent_pks = {x.pk for x in self.agents}
        # self.agent_pks = {agent1.pk, agent2.pk, agent3.pk}
        self.categories_by_task = self.get_categories_by_task()
        # self.categories_by_task[task.pk] = {category1.pk, category2.pk, category3.pk}
        self.tasks_by_category = self.get_tasks_by_category()
        # self.tasks_by_categories[category.pk] = {task1, task2, task3}
        self.agent_exclusions_by_category = self.get_agent_exclusions_by_category()
        # self.agent_exclusions_by_category[category.pk] = {agent1.pk, agent2.pk, agent3.pk}
        self.agent_exclusions_by_task = self.get_agent_exclusions_by_task()
        # self.agent_exclusions_by_task[task.pk] = {agent1.pk, agent2.pk, agent3.pk}
        self.preferences_by_agent_by_category = self.get_preferences_by_agent_by_category()
        # self.preferences_by_agent_by_category[category.pk][agent.pk] = (balancing_offset, balancing_count, affinity)
        self.max_task_affectations_by_category = self.get_max_task_affectations_by_category()
        # self.max_task_affectations_by_category[category.pk] = [max_task_affectation_1, max_task_affectation_2]
        self.available_agents_by_tasks = {task.pk: (self.agent_pks - self.agent_exclusions_by_task[task.pk])
                                          for task in self.tasks}

    def get_categories_by_task(self):
        result = {x.pk: set() for x in self.tasks}
        for related in Task.categories.through.objects.filter(category__id__in=self.categories_by_pk):
            result[related.task_id].add(related.category_id)
        return result

    def get_tasks_by_category(self):
        result = {x.pk: set() for x in self.categories}
        tasks_by_pk = {x.pk: x for x in self.tasks}
        for task_pk, category_pks in self.categories_by_task.items():
            for category_pk in category_pks:
                result[category_pk].add(tasks_by_pk[task_pk])
        return result

    def get_agent_exclusions_by_category(self):
        agent_exclusions_by_category = {category.pk: set() for category in self.categories}
        for a in self.agent_category_preferences:
            if a.balancing_count is None:
                agent_exclusions_by_category[a.category_id].add(a.agent_id)
        return agent_exclusions_by_category

    def get_agent_exclusions_by_task(self):
        agent_task_exclusions = {task.pk: set() for task in self.tasks}
        for task in self.tasks:
            task_pk = task.pk
            for category_pk in self.categories_by_task[task_pk]:
                for agent_pk in self.agent_exclusions_by_category[category_pk]:
                    agent_task_exclusions[task_pk].add(agent_pk)
            for agent in self.agents:
                # TODO optimize
                if agent.start_time is not None and agent.start_time > task.start_time:
                    agent_task_exclusions[task_pk].add(agent.pk)
                elif agent.end_time is not None and agent.end_time < task.end_time:
                    agent_task_exclusions[task_pk].add(agent.pk)
        for agent_task_exclusion in self.organization.agenttaskexclusion_set.all():
            agent_task_exclusions[agent_task_exclusion.task_pk].add(agent_task_exclusion.agent_id)
        return agent_task_exclusions

    def get_preferences_by_agent_by_category(self):
        preferences = {c.pk: {} for c in self.categories}
        for a in self.agent_category_preferences:
            preferences[a.category_id][a.agent_id] = (a.balancing_offset, a.balancing_count, a.affinity)
        return preferences

    def get_max_task_affectations_by_category(self):
        max_task_affectations_by_category = {x.pk: [] for x in self.categories}
        for max_affectation in self.organization.maxtaskaffectation_set.all():
            max_task_affectations_by_category[max_affectation.category_id].append(max_affectation)
        for max_affectation in self.organization.maxtimetaskaffectation_set.all():
            max_task_affectations_by_category[max_affectation.category_id].append(max_affectation)
        return max_task_affectations_by_category

    def apply_max_task_affectations(self, category_pk: int):
        """ "Agent A cannot execute more than X tasks of category C in less than T time slices"
        :param category_pk:
        """
        task_data = [(task.pk, task.start_time, task.end_time) for task in self.tasks_by_category[category_pk]]
        task_data.sort(key=lambda x: (x[1], x[2]))
        agent_pks = self.agent_pks - self.agent_exclusions_by_category[category_pk]
        previous_start_time = None
        for index, data in enumerate(task_data):
            task_pk, start_time, __ = data
            if start_time == previous_start_time:
                continue
            current_tasks = {task_pk}
            for max_affectation in self.max_task_affectations_by_category[category_pk]:
                end_block_time_slice = start_time + max_affectation.range_time_slice
                for data_2 in task_data[index + 1:]:
                    task_pk_2, start_time_2, __ = data_2
                    if start_time_2 >= end_block_time_slice:
                        break
                    current_tasks.add(task_pk_2)
                direction = '<=' if max_affectation.mode == max_affectation.MAXIMUM else '>='
                if isinstance(max_affectation, MaxTimeTaskAffectation):
                    for agent_pk in agent_pks:
                        variables = ['%d * %s' % (self.task_durations[task_pk], self.variable(agent_pk, task_pk))
                                     for task_pk in current_tasks]
                        yield Constraint('%s %s %d' % (' + '.join(variables), direction,
                                                       max_affectation.task_maximum_time))
                else:
                    for agent_pk in agent_pks:
                        variables = [self.variable(agent_pk, task_pk) for task_pk in current_tasks]
                        yield Constraint('%s %s %d' % (' + '.join(variables), direction,
                                                       max_affectation.task_maximum_count))
            previous_start_time = start_time

    def apply_all_tasks_must_be_done(self):
        """ "Exactly one agent must perform each task"
        """
        for task_pk, task_agent_pks in self.available_agents_by_tasks.items():
            yield Constraint('%s = 1' % ' + '.join([self.variable(agent_pk, task_pk) for agent_pk in task_agent_pks]))
            if len(task_agent_pks) == len(self.agent_pks):
                continue
            yield Constraint('%s = 1' % ' + '.join([self.variable(agent_pk, task_pk) for agent_pk in self.agent_pks]))

    def apply_fixed_tasks(self):
        """ "Task E must be performed by agent A" """
        for task in self.tasks:
            if task.fixed and task.agent_id:
                yield Constraint('%s = 1' % self.variable(task.agent_id, task.pk))

    def apply_single_task_per_agent(self):
        """ "Agent X can perform at most one task (of the same category) at a time" """
        current_tasks = set()
        resumed_tasks = {}
        for task in self.tasks:
            resumed_tasks.setdefault(task.start_time, []).append((task.pk, current_tasks.add))
            resumed_tasks.setdefault(task.end_time, []).append((task.pk, current_tasks.remove))
        time_slices = [x for x in resumed_tasks]
        time_slices.sort()
        for time_slice in time_slices:
            for (task_pk, action) in resumed_tasks[time_slice]:
                action(task_pk)
            if not current_tasks:
                continue
            current_tasks_by_category = {}
            for task_pk in current_tasks:
                for category_pk in self.categories_by_task[task_pk]:
                    current_tasks_by_category.setdefault(category_pk, set()).add(task_pk)
            for agent_pk in self.agent_pks:
                for current_task_subset in current_tasks_by_category.values():
                    variables = [self.variable(agent_pk, task_pk) for task_pk in current_task_subset]
                    yield Constraint('%s <= 1' % ' + '.join(variables))

    def apply_balancing_constraints(self):
        for category in self.categories:
            if category.balancing_mode is None or category.balancing_tolerance is None:
                continue
            category_pk = category.pk
            cat_task_pks = [task.pk for task in self.tasks_by_category[category_pk]]
            cat_agent_pks = self.agent_pks - self.agent_exclusions_by_category[category_pk]
            for agent_pk in cat_agent_pks:
                agent_preferences = self.preferences_by_agent_by_category[category_pk].get(agent_pk, (0, 1., 0.))
                if category.balancing_mode == category.BALANCE_NUMBER:
                    ag_sum = ['%g * %s' % (agent_preferences[1], self.variable(agent_pk, task_pk))
                              for task_pk in cat_task_pks]
                else:
                    ag_sum = ['%g * %d * %s' % (agent_preferences[1], self.task_durations[task_pk],
                                                self.variable(agent_pk, task_pk)) for task_pk in cat_task_pks]
                yield Constraint('%g + %s = %s' % (agent_preferences[0] * agent_preferences[1], ' + '.join(ag_sum),
                                                   self.category_variable(category_pk, agent_pk)))
            ag_sum = [self.category_variable(category_pk, agent_pk) for agent_pk in cat_agent_pks]
            yield Constraint('%s = %s' % (' + '.join(ag_sum), self.category_variable(category_pk)))
            for agent_pk in cat_agent_pks:
                count = len(cat_agent_pks)
                yield Constraint(
                    '%d * %s <= %s + %g' % (count, self.category_variable(category_pk, agent_pk),
                                            self.category_variable(category_pk), category.balancing_tolerance * count))
                yield Constraint(
                    '%d * %s >= %s - %g' % (count, self.category_variable(category_pk, agent_pk),
                                            self.category_variable(category_pk), category.balancing_tolerance * count)
                )

    def compute_balancing(self, result_list):
        """Return a dict
        :return {category.pk: (name, mode, max_value_among_all_agents - min_value_among_all_agents)}"""
        balances = {}

        result_dict = {}
        for agent_pk, task_pk in result_list:
            print(agent_pk, task_pk)
            result_dict.setdefault(agent_pk, set()).add(task_pk)

        def is_affected_to(agent_pk_, task_pk_):
            return 1 if (agent_pk_ in result_dict and task_pk_ in result_dict[agent_pk_]) else 0

        for category in self.categories:
            if category.balancing_mode is None or category.balancing_tolerance is None:
                continue
            category_pk = category.pk
            cat_task_pks = [task.pk for task in self.tasks_by_category[category_pk]]
            cat_agent_pks = self.agent_pks - self.agent_exclusions_by_category[category_pk]
            cat_min = None
            cat_max = None
            for agent_pk in cat_agent_pks:
                agent_preferences = self.preferences_by_agent_by_category[category_pk].get(agent_pk, (0, 1., 0.))
                if category.balancing_mode == category.BALANCE_NUMBER:
                    ag_sum = sum((agent_preferences[1] * is_affected_to(agent_pk, task_pk)) for task_pk in cat_task_pks)
                else:
                    ag_sum = sum((agent_preferences[1] * self.task_durations[task_pk] *
                                  is_affected_to(agent_pk, task_pk)) for task_pk in cat_task_pks)
                ag_offset = agent_preferences[0] * agent_preferences[1]
                ag_total = ag_sum + ag_offset
                if cat_min is None or cat_min > ag_total:
                    cat_min = ag_total
                if cat_max is None or cat_max < ag_total:
                    cat_max = ag_total
            if cat_min is not None:
                balances[category_pk] = (category.name, category.balancing_mode, cat_max - cat_min)
        return balances

    def apply_affinity_constraints(self):
        variables = []
        for category in self.categories:
            category_pk = category.pk
            cat_task_pks = [(task.pk, task.start_time, task.end_time) for task in self.tasks_by_category[category_pk]]
            # if category.auto_affinity:
            # cat_task_pks.sort(key=lambda x: x[1])
            for agent_pk in self.agent_pks - self.agent_exclusions_by_category[category_pk]:
                agent_preferences = self.preferences_by_agent_by_category[category_pk].get(agent_pk, (0, 1., 0.))
                variables += ['%g * %s' % (agent_preferences[2], self.variable(agent_pk, x[0]))
                              for x in cat_task_pks if agent_preferences[2]]
        if variables:
            yield Constraint('min: -%s' % self.affinity_variable())
            yield Constraint('%s = %s' % (' + '.join(variables), self.affinity_variable()))
        else:
            yield Constraint('min:')

    def constraints(self):
        yield from self.apply_affinity_constraints()
        # all tasks must be done
        yield from self.apply_all_tasks_must_be_done()
        # task with a fixed agent
        yield from self.apply_fixed_tasks()
        # at most one task by agent at the same time
        yield from self.apply_single_task_per_agent()
        for category in self.categories:
            if self.max_task_affectations_by_category[category.pk]:
                yield from self.apply_max_task_affectations(category.pk)
        yield from self.apply_balancing_constraints()
        for task_pk, agent_pks in self.available_agents_by_tasks.items():
            for agent_pk in agent_pks:
                yield Constraint('%s >= 0' % self.variable(agent_pk, task_pk))
                yield Constraint('%s <= 1' % self.variable(agent_pk, task_pk))
        for task_pk, agent_pks in self.available_agents_by_tasks.items():
            for agent_pk in agent_pks:
                yield Constraint('int %s' % self.variable(agent_pk, task_pk))

    @staticmethod
    def variable(agent_pk, task_pk):
        return 'v_a%s_e%s' % (agent_pk, task_pk)

    result_line_re = r'^v_a(\d+)_e(\d+)\s+1$'

    @staticmethod
    def category_variable(category_pk, agent_pk=None):
        if agent_pk is None:
            return 'c_c%s' % category_pk
        return 'c_c%s_a%s' % (category_pk, agent_pk)

    @staticmethod
    def affinity_variable():
        return 'a'

    def solve(self, verbose=False, max_compute_time=None, schedule_run=None):
        """ Return a schedule (if such one exists) as a list of (agent_pk, task_pk)
        :param verbose: print the result to stdout
        :param max_compute_time: max compute time
        :param schedule_run: a ScheduleRun object to update with its process id (must have its "id" attribute)
        :return:
        :rtype:
        """
        if max_compute_time is not None and max_compute_time <= 0:
            max_compute_time = None
        with tempfile.NamedTemporaryFile() as fd:
            for constraint in self.constraints():
                if verbose:
                    print(constraint)
                fd.write(('%s;\n' % constraint).encode())
            fd.flush()
            cmd = [settings.LP_SOLVE_PATH, '-lp', fd.name]
            if max_compute_time:
                cmd += ['-timeout', str(max_compute_time)]
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
            if schedule_run:
                ScheduleRun.objects.filter(pk=schedule_run.pk).update(process_id=p.pid)
            std_out, std_err = p.communicate(timeout=max_compute_time)
            if schedule_run:
                ScheduleRun.objects.filter(pk=schedule_run.pk).update(process_id=None)
        if verbose:
            print(std_out.decode())
            print(std_err.decode())
        result_list = []
        std_out = std_out.decode()
        value_re = re.compile(self.result_line_re)
        for line in std_out.splitlines():
            matcher = value_re.match(line)
            if matcher:
                result_list.append((int(matcher.group(1)), int(matcher.group(2))))
        return result_list

    @staticmethod
    def result_by_agent(result_list):
        result_dict = {}
        for agent_pk, task_pk in result_list:
            result_dict.setdefault(agent_pk, set()).add(task_pk)
        return result_dict

    @staticmethod
    def result_by_task(result_list):
        result_dict = {}
        for agent_pk, task_pk in result_list:
            result_dict.setdefault(task_pk, set()).add(agent_pk)
        return result_dict
