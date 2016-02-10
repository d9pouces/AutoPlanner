# -*- coding=utf-8 -*-
from __future__ import unicode_literals
import re
import subprocess
import tempfile
import datetime

__author__ = 'mgallet'


class Scheduler(object):
    def __init__(self, agents, forbidden_weeks, only_p2_weeks=None, weak_weeks=None, fixed_weeks=None,
                 p1_tolerance=0, p2_tolerance=1, p1_offsets=None, p2_offsets=None,
                 p1_offloads=None, p2_offloads=None):
        """
        :param agents: liste des agents
        :param forbidden_weeks: forbidden_weeks[agent] = liste des semaines d'absence complète (ni P1, ni P2, ni P3)
        :param only_p2_weeks: only_p2_weeks[agent] = liste des semaines d'absence partielle (peut être P2 ou P3 uniquement)
        :param weak_weeks: liste des semaines sans P3
        :param fixed_weeks: fixed_weeks[week][position] = agent : affectations inviolables (par exemple pour le passé)
        :param p1_tolerance: le nombre de P1 doit être le même pour tout le monde à 'p1_tolerance' près
        :param p2_tolerance: le nombre de P2 doit être le même pour tout le monde à 'p2_tolerance' près
        :param p1_offsets: p1_offsets[agent] = nombre de P1 d'avance (>0) ou de retard (<0) pour l'agent
        :param p2_offsets: p2_offsets[agent] = nombre de P2 d'avance (>0) ou de retard (<0) pour l'agent
        :param p1_offloads: p1_offloads[agent] = si < 1.0 : l'agent fait moins de P1
        :param p2_offloads: p2_offloads[agent] = si < 1.0 : l'agent fait moins de P2
        :return:
        """
        self.agents = agents  # [agent1, agent2, agent3, ]
        self.forbidden_weeks = forbidden_weeks  # forbidden_weeks[agent] = [week1, week2, week3, ..]
        self.only_p2_weeks = only_p2_weeks or {}  # only_p2_weeks[agent] = [week1, week2, week3, ..]
        self.fixed_weeks = fixed_weeks or {}  # existing_weeks[week] = {position: agent, }
        self.weak_weeks = weak_weeks or {}  # set of 2-person-only weeks
        self.p1_offloads = p1_offloads or {}  # p1_offloads[agent] = float (> 1. => more P1s, < 1. : fewer P1s)
        self.p2_offloads = p2_offloads or {}  # p2_offloads[agent] = float (> 1. => more P2/3s, < 1. : fewer P2/3s)
        self.p1_offsets = p1_offsets or {}  # p1_offsets[agent] = int
        self.p2_offsets = p2_offsets or {}  # p2_offsets[agent] = int
        self.p1_tolerance = p1_tolerance
        self.p2_tolerance = p2_tolerance
        for agent in agents:
            self.forbidden_weeks.setdefault(agent, [])
            self.only_p2_weeks.setdefault(agent, [])
            self.p1_offsets.setdefault(agent, 0)
            self.p2_offsets.setdefault(agent, 0)
            self.p1_offloads.setdefault(agent, 1.)
            self.p2_offloads.setdefault(agent, 1.)

    @staticmethod
    def variable(position=1, agent='mgallet', week=1):
        return 'p%d_%s_%d' % (position, agent, week)

    def constraint_list(self, start_week=1, end_week=52):
        weeks = range(start_week, end_week + 1)
        positions = range(1, 4)
        yield 'min: '
        for week in weeks:
            for agent in self.agents:
                if week not in self.forbidden_weeks[agent]:
                    for position in positions:
                        yield "%s >= 0" % self.variable(position, agent, week)
                        yield "%s <= 1" % self.variable(position, agent, week)
                    # The same person can only be P1, P2 xor P3
                    yield '%s <= 1' % ' + '.join([self.variable(position, agent, week) for position in positions])
                    if week in self.only_p2_weeks[agent]:
                        yield "%s = 0" % self.variable(1, agent, week)
                else:
                    # Respect the personal constraints of each person
                    for position in positions:
                        yield "%s = 0" % self.variable(position, agent, week)
        # respect the existing weeks
        for week, week_data in self.fixed_weeks.items():
            for position, agent in week_data.items():
                yield "%s = 1" % self.variable(position, agent, week)
        for week in weeks:
            # Exactly one person in P1 for each week
            yield '%s = 1' % ' + '.join([self.variable(1, agent, week) for agent in self.agents])
            # Exactly one person in P2 for each week
            yield '%s = 1' % ' + '.join([self.variable(2, agent, week) for agent in self.agents])
            if week not in self.weak_weeks:
                # Exactly one person in P3 for each week
                yield '%s = 1' % ' + '.join([self.variable(3, agent, week) for agent in self.agents])
        # P1 cannot be the same for two successive weeks
        for week in range(start_week, end_week):
            for agent in self.agents:
                yield '%s + %s <= 1' % (self.variable(1, agent, week), self.variable(1, agent, week + 1))
        # the same person cannot be P1, P2, P3 for four successive weeks
        for week in range(start_week, end_week - 3):
            for agent in self.agents:
                week_1 = ' + '.join([self.variable(position, agent, week) for position in positions])
                week_2 = ' + '.join([self.variable(position, agent, week + 1) for position in positions])
                week_3 = ' + '.join([self.variable(position, agent, week + 2) for position in positions])
                week_4 = ' + '.join([self.variable(position, agent, week + 3) for position in positions])
                yield '%s + %s + %s + %s <= 3' % (week_1, week_2, week_3, week_4)

        for agent in self.agents:
            # number of P1s and P2/3s of each agent
            yield '%s = p1_sum_%s' % (' + '.join([self.variable(1, agent, week) for week in weeks]), agent)
            yield '%s + %s = p23_sum_%s' % (' + '.join([self.variable(2, agent, week) for week in weeks]),
                                            ' + '.join([self.variable(3, agent, week) for week in weeks]), agent)
        # (some agents can execute less P1s than others)
        # balance of P1s between agents, taking into account previous P1s and external work
        offload_terms = []
        for agent in self.agents:
            offload_terms.append('%g * p1_sum_%s + %g' %
                                 (1. / (self.p1_offloads[agent]), agent,
                                  1. * self.p1_offsets[agent] / self.p1_offloads[agent]))
        yield '%s = p1_sum' % ' + '.join(offload_terms)
        for agent in self.agents:
            yield '%g + %g * p1_sum_%s <= %g * p1_sum + %g' % (1. * self.p1_offsets[agent] / self.p1_offloads[agent],
                                                               1. / self.p1_offloads[agent],
                                                               agent, 1. / len(self.agents), self.p1_tolerance)
            yield '%g + %g * p1_sum_%s >= %g * p1_sum - %g' % (1. * self.p1_offsets[agent] / self.p1_offloads[agent],
                                                               1. / self.p1_offloads[agent],
                                                               agent, 1. / len(self.agents), self.p1_tolerance)
        # balance of P2s between agents, taking into account previous P2/P3s and external work
        # (some agents can execute less P2s and P3s than others)
        offload_terms = []
        for agent in self.agents:
            offload_terms.append('%g * p23_sum_%s + %g' %
                                 (1. / (self.p2_offloads[agent]), agent,
                                  1. * self.p2_offsets[agent] / self.p2_offloads[agent]))
        yield '%s = p23_sum' % ' + '.join(offload_terms)
        for agent in self.agents:
            yield '%g + %g * p23_sum_%s <= %g * p23_sum + %g' % (1. * self.p2_offsets[agent] / self.p2_offloads[agent],
                                                                 1. / self.p2_offloads[agent],
                                                                 agent, 1. / len(self.agents), self.p2_tolerance)
            yield '%g + %g * p23_sum_%s >= %g * p23_sum - %g' % (1. * self.p2_offsets[agent] / self.p2_offloads[agent],
                                                                 1. / self.p2_offloads[agent],
                                                                 agent, 1. / len(self.agents), self.p2_tolerance)
        # integer constraints
        for position in positions:
            for week in weeks:
                for agent in self.agents:
                    yield 'int %s' % self.variable(position, agent, week)

    def solve(self, start_week=1, end_week=52, verbose=False):
        with tempfile.NamedTemporaryFile() as fd:
            for constraint in self.constraint_list(start_week=start_week, end_week=end_week):
                if verbose:
                    print(constraint)
                fd.write('%s;\n' % constraint)
            fd.flush()
            p = subprocess.Popen(['lp_solve', '-lp', fd.name], stdout=subprocess.PIPE)
            std_out, std_err = p.communicate()
        results_per_week = {}
        regexp = re.compile(r'p(\d+)_([a-z]+)_(\d+)\s+(0|1)')
        p1_per_agent = {agent: 0 for agent in self.agents}
        p2_p3_per_agent = {agent: 0 for agent in self.agents}
        for line in std_out.splitlines():
            matcher = regexp.match(line)
            if not matcher:
                continue
            position_str, agent, week_str, value = matcher.groups()
            if value != '1':
                continue
            position = int(position_str)
            week = int(week_str)
            results_per_week.setdefault(week, {})[position] = agent
            if position == 1:
                p1_per_agent[agent] += 1
            elif position == 2 or position == 3:
                p2_p3_per_agent[agent] += 1
        weeks = [week for week in results_per_week]
        weeks.sort()
        for week, week_data in results_per_week.items():
            d = datetime.datetime.strptime('2016-%d-1' % week, '%Y-%W-%w')
            start = (d - datetime.timedelta(days=3)).strftime('%d/%m/%Y')
            end = (d + datetime.timedelta(days=4)).strftime('%d/%m/%Y')
            print('    Semaine %s [%s 18h -> %s 18h]: P1 = %s, P2 = %s, P3 = %s' %
                  (week, start, end, week_data[1], week_data.get(2, '--'), week_data.get(3, '--')))
        print('Par agent :')
        for agent in self.agents:
            print('    %s : %d P1, %d P2 + P3' % (agent, p1_per_agent[agent], p2_p3_per_agent[agent]))
        print('Nouvelles contraintes :')
        for week, week_data in results_per_week.items():
            print('%s: {%s},' % (week, ', '.join(["%d: '%s'" % (x, y) for (x, y) in week_data.items()])))
