# -*- coding: utf-8 -*-

import celery
import json
import signal

import os
import subprocess
from django.utils.formats import date_format, time_format
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from djangofloor.celery import app

from autoplanner.models import Organization, Task, ScheduleRun, Agent
from autoplanner.schedule import Scheduler

# used to avoid strange import bug with Python 3.2/3.3
# noinspection PyStatementEffect
celery.__file__
from celery import shared_task


__author__ = 'Matthieu Gallet'


@shared_task(serializer='json', bind=True)
def compute_schedule(self, organization_id):
    celery_id = self.request.id
    start = timezone.localtime(timezone.now())
    count = Organization.objects \
        .filter(pk=organization_id, celery_task_id=None) \
        .update(celery_task_id=celery_id, celery_start=start,
                message=_('Computation started at %(d)s, %(t)s') % {'d': date_format(start, use_l10n=True),
                                                                    't': time_format(start, use_l10n=True)})
    if count == 0:
        print('organization not found')
        return
    organization = Organization.objects.get(pk=organization_id, celery_task_id=celery_id)
    schedule_run = ScheduleRun(organization=organization, celery_task_id=celery_id, celery_start=start)
    schedule_run.save()
    print('schedule launched for %s' % organization)
    scheduler = Scheduler(organization)
    try:
        result_list = scheduler.solve(verbose=True, max_compute_time=organization.max_compute_time)
        result_dict = scheduler.result_by_agent(result_list)
        apply_schedule(organization_id, result_dict)
        end = timezone.localtime(timezone.now())
        print('schedule finished for %s' % organization)
        if result_dict:
            message = _('Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                                   't': time_format(end, use_l10n=True)}
        else:
            message = _('Unable to find a solution, maybe you should remove some constraints. '
                        'Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                                   't': time_format(end, use_l10n=True)}
        serialized_result_dict = json.dumps(result_dict)
        ScheduleRun.objects.filter(pk=schedule_run.pk).update(celery_end=end, process_id=None, status=bool(result_dict),
                                                              result_dict=serialized_result_dict)
    except subprocess.TimeoutExpired:
        end = timezone.localtime(timezone.now())
        message = _('%(d)s, %(t)s: Unable to find a schedule in the allowed time.') % \
                  {'d': date_format(end, use_l10n=True), 't': time_format(end, use_l10n=True)}
        ScheduleRun.objects.filter(pk=schedule_run.pk).update(celery_end=end, process_id=None, status=False)
    except Exception as e:
        end = timezone.localtime(timezone.now())
        message = _('%(d)s, %(t)s: Unable to compute a schedule %(msg)s') % \
                  {'msg': e, 'd': date_format(end, use_l10n=True), 't': time_format(end, use_l10n=True)}
        ScheduleRun.objects.filter(pk=schedule_run.pk).update(celery_end=end, process_id=None, status=False)

    Organization.objects.filter(pk=organization_id, celery_task_id=celery_id) \
        .update(celery_task_id=None, message=message)


def apply_schedule(organization_id, result_dict):
    """Update all tasks to set the right agent"""
    available_agent_ids = {x[0] for x in Agent.objects.filter(organization__id=organization_id).values_list('id')}
    available_tasks_ids = {x[0] for x in Task.objects.filter(organization__id=organization_id).values_list('id')}
    for agent_pk, task_pks in result_dict.items():
        if agent_pk not in available_agent_ids:
            raise ValueError(_('Invalid schedule: an agent has been removed since this computation.'))
        elif not set(task_pks).issubset(available_tasks_ids):
            raise ValueError(_('Invalid schedule: a task has been removed since this computation.'))
    for agent_pk, task_pks in result_dict.items():
        Task.objects.filter(pk__in=task_pks, fixed=False, organization__id=organization_id) \
            .update(agent_id=agent_pk)


@shared_task(serializer='json', bind=True)
def kill_schedule(self, celery_task_id):
    # noinspection PyUnusedLocal
    self = self
    app.control.revoke(celery_task_id)
    all_process_ids = []
    for values in ScheduleRun.objects.filter(celery_task_id=celery_task_id).values_list('process_id'):
        # noinspection PyBroadException
        try:
            os.kill(values[0], signal.SIGKILL)
            all_process_ids.append(values[0])
        except:
            pass
    end = timezone.localtime(timezone.now())
    ScheduleRun.objects.filter(celery_task_id=celery_task_id, process_id__in=all_process_ids)\
        .update(process_id=None, celery_end=end)
    Organization.objects.filter(celery_task_id=celery_task_id)\
        .update(celery_task_id=None, celery_end=end,
                message=_('Computation killed at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                                   't': time_format(end, use_l10n=True)})
