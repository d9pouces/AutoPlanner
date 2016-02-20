# -*- coding: utf-8 -*-
import datetime
from django.test import TestCase
from django.utils.timezone import utc
from autoplanner.models import Organization, Agent, Category, Task
from autoplanner.schedule import Scheduler

__author__ = 'Matthieu Gallet'


class BaseTest(TestCase):
    def get_organization(self):
        org = Organization(name='O')
        org.save()
        agent_1 = Agent(organization=org, name='A1')
        agent_1.save()
        agent_2 = Agent(organization=org, name='A2')
        agent_2.save()
        agent_3 = Agent(organization=org, name='A3')
        agent_3.save()
        category_0 = Category(organization=org, name='C0')
        category_0.save()
        category_1 = Category(organization=org, name='C1', parent_category=category_0)
        category_1.save()
        category_2 = Category(organization=org, name='C2', parent_category=category_0)
        category_2.save()
        return org


class TestSimple(BaseTest):
    def test_empty(self):
        org = self.get_organization()
        s = Scheduler(org)
        self.assertEqual(['min:'], [str(x) for x in s.constraints()])

    def get_time(self, value):
        return datetime.datetime(2016, 1, 1, value, 0, 0, tzinfo=utc)

    def test_single(self):
        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        task_1 = Task(organization=org, name='E1', start_time=self.get_time(0), end_time=self.get_time(1),
                      category=category_1)
        task_1.save()
        # s = Scheduler(org)
        # for c in s.constraints():
        # print(c)

        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        category_1.balancing_mode = Category.BALANCE_NUMBER
        category_1.save()
        task_1 = Task(organization=org, name='E1', start_time=self.get_time(0), end_time=self.get_time(1),
                      category=category_1)
        task_1.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({4: {2}}, result_dict)

    def test_simple_balance(self):
        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        assert isinstance(category_1, Category)
        category_1.balancing_mode = Category.BALANCE_NUMBER
        category_1.balancing_tolerance = 0
        category_1.save()
        task_1 = Task(organization=org, name='E1', start_time=self.get_time(0), end_time=self.get_time(1),
                      category=category_1)
        task_1.save()
        task_2 = Task(organization=org, name='E2', start_time=self.get_time(1), end_time=self.get_time(2),
                      category=category_1)
        task_2.save()
        task_3 = Task(organization=org, name='E3', start_time=self.get_time(2), end_time=self.get_time(3),
                      category=category_1)
        task_3.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({1: {3}, 2: {2}, 3: {1}}, result_dict)

    def test_infeasible(self):
        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        assert isinstance(category_1, Category)
        category_1.balancing_mode = Category.BALANCE_NUMBER
        category_1.balancing_tolerance = 0
        category_1.save()
        task_1 = Task(organization=org, name='E1', start_time=self.get_time(0), end_time=self.get_time(1),
                      category=category_1)
        task_1.save()
        task_2 = Task(organization=org, name='E2', start_time=self.get_time(1), end_time=self.get_time(2),
                      category=category_1)
        task_2.save()
        task_3 = Task(organization=org, name='E3', start_time=self.get_time(2), end_time=self.get_time(3),
                      category=category_1)
        task_3.save()
        task_4 = Task(organization=org, name='E4', start_time=self.get_time(3), end_time=self.get_time(4),
                      category=category_1)
        task_4.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({}, result_dict)
        category_1.balancing_tolerance = 1
        category_1.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({1: {1, 2}, 2: {3}, 3: {4}}, result_dict)

    def test_overlap(self):
        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        Agent.objects.filter(organization=org, name__in=['A2', 'A3']).delete()
        task_1 = Task(organization=org, name='E1', start_time=self.get_time(10), end_time=self.get_time(20),
                      category=category_1)
        task_1.save()
        task_2 = Task(organization=org, name='E2', start_time=self.get_time(15), end_time=self.get_time(23),
                      category=category_1)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({}, result_dict)

        task_2.start_time = self.get_time(21)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({1: {1, 2}}, result_dict)

        task_2.start_time = self.get_time(20)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({1: {1, 2}}, result_dict)

        task_2.start_time = self.get_time(5)
        task_2.end_time = self.get_time(10)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({1: {1, 2}}, result_dict)

        task_2.start_time = self.get_time(5)
        task_2.end_time = self.get_time(11)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({}, result_dict)

        task_2.start_time = self.get_time(5)
        task_2.end_time = self.get_time(23)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({}, result_dict)

        task_2.start_time = self.get_time(12)
        task_2.end_time = self.get_time(17)
        task_2.save()
        s = Scheduler(org)
        result_list = s.solve(verbose=False)
        result_dict = s.result_by_agent(result_list)
        self.assertEqual({}, result_dict)
