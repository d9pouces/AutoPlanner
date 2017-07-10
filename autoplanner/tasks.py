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


class SetJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, set):
            return list(o)
        return super().default(o)


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
        return
    organization = Organization.objects.get(pk=organization_id, celery_task_id=celery_id)
    schedule_run = ScheduleRun(organization=organization, celery_task_id=celery_id, celery_start=start)
    schedule_run.save()
    scheduler = Scheduler(organization)
    try:
        result_list = scheduler.solve(verbose=False, max_compute_time=organization.max_compute_time,
                                      schedule_run=schedule_run)
        result_dict = scheduler.result_by_agent(result_list)
        end = timezone.localtime(timezone.now())
        selected = bool(result_dict)
        if selected:
            apply_schedule(organization_id, result_dict)
            msg = _('Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                               't': time_format(end, use_l10n=True)}
            balancing = scheduler.compute_balancing(result_list)
            if balancing:
                balances = _(', ').join(['%s: %s' % (x[0], x[2]) for x in balancing.values()])
                schedule_msg = _('Balancing: %(b)s') % {'b': balances}
            else:
                schedule_msg = _('No balance required.')
            ScheduleRun.objects.filter(organization__id=organization_id).update(is_selected=False)
        else:
            schedule_msg = _('Unable to find a solution')
            msg = _('Unable to find a solution, maybe you should remove some constraints. '
                    'Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                               't': time_format(end, use_l10n=True)}
        serialized_result_dict = json.dumps(result_dict, cls=SetJSONEncoder)
        ScheduleRun.objects.filter(pk=schedule_run.pk).update(celery_end=end, process_id=None, status=bool(result_dict),
                                                              result_dict=serialized_result_dict, is_selected=selected,
                                                              message=schedule_msg)
    except subprocess.TimeoutExpired:
        end = timezone.localtime(timezone.now())
        msg = _('%(d)s, %(t)s: Unable to find a schedule in the allowed time.') % \
            {'d': date_format(end, use_l10n=True), 't': time_format(end, use_l10n=True)}
        ScheduleRun.objects.filter(pk=schedule_run.pk).update(celery_end=end, process_id=None, status=False)
    except Exception as e:
        end = timezone.localtime(timezone.now())
        msg = _('%(d)s, %(t)s: Unable to compute a schedule %(msg)s') % \
            {'msg': e, 'd': date_format(end, use_l10n=True), 't': time_format(end, use_l10n=True)}
        ScheduleRun.objects.filter(pk=schedule_run.pk).update(celery_end=end, process_id=None, status=False)

    Organization.objects.filter(pk=organization_id, celery_task_id=celery_id) \
        .update(celery_task_id=None, message=msg)


def apply_schedule(organization_id, result_dict):
    """Update all tasks to set the right agent"""
    available_agent_ids = {x[0] for x in Agent.objects.filter(organization__id=organization_id).values_list('id')}
    available_tasks_ids = {x[0] for x in Task.objects.filter(organization__id=organization_id).values_list('id')}
    all_task_pks = set()
    for agent_pk, task_pks in result_dict.items():
        agent_pk = int(agent_pk)
        task_pks = set(task_pks)
        if agent_pk not in available_agent_ids:
            raise ValueError(_('Invalid schedule: an agent has been removed since this computation'))
        elif not task_pks.issubset(available_tasks_ids):
            raise ValueError(_('Invalid schedule: a task has been removed since this computation'))
        all_task_pks |= task_pks
    if not available_tasks_ids.issubset(all_task_pks):
        raise ValueError(_('Invalid schedule: several tasks are not affected to an agent'))
    for agent_pk, task_pks in result_dict.items():
        agent_pk = int(agent_pk)
        Task.objects.filter(pk__in=task_pks, fixed=False, organization__id=organization_id) \
            .update(agent_id=agent_pk)


@shared_task(serializer='json', bind=True)
def kill_schedule(self, celery_task_id):
    # noinspection PyUnusedLocal
    self = self
    app.control.revoke(celery_task_id)
    all_process_ids = []
    for values in ScheduleRun.objects.filter(celery_task_id=celery_task_id).values_list('process_id'):
        if values[0]:
            # noinspection PyBroadException
            try:
                os.kill(values[0], signal.SIGKILL)
                all_process_ids.append(values[0])
            except:
                pass
    end = timezone.localtime(timezone.now())
    ScheduleRun.objects.filter(celery_task_id=celery_task_id, process_id__in=all_process_ids) \
        .update(process_id=None, celery_end=end)
    Organization.objects.filter(celery_task_id=celery_task_id) \
        .update(celery_task_id=None, celery_end=end,
                message=_('Computation killed at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                                   't': time_format(end, use_l10n=True)})
