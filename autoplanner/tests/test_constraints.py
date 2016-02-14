# -*- coding: utf-8 -*-
from django.test import TestCase
from autoplanner.models import Organization, Agent, Category, Event

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
        self.assertEqual(['0 = a'], list(org.constraints()))

    def test_single(self):
        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        event_1 = Event(organization=org, name='E1', start_time_slice=0, end_time_slice=1, category=category_1)
        event_1.save()
        for c in org.constraints():
            print(c)
        org = self.get_organization()
        category_1 = org.category_set.get(name='C1')
        category_1.balancing_mode = Category.BALANCE_NUMBER
        category_1.save()
        event_1 = Event(organization=org, name='E1', start_time_slice=0, end_time_slice=1, category=category_1)
        event_1.save()
        for c in org.constraints():
            print(c)
