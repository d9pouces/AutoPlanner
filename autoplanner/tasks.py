# -*- coding: utf-8 -*-

import celery
from django.utils.formats import date_format, time_format
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from autoplanner.models import Organization, Task
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
    print('schedule launched for %s' % organization)
    scheduler = Scheduler(organization)
    result_list = scheduler.solve(verbose=True)
    result_dict = scheduler.result_by_agent(result_list)
    for agent_pk, task_pks in result_dict.items():
        c = Task.objects.filter(pk__in=task_pks, fixed=False, organization__id=organization_id)\
            .update(agent_id=agent_pk)
        if c == 0:
            print('erreur task %s agent %d' % (task_pks, agent_pk))
    end = timezone.localtime(timezone.now())
    print('schedule finished for %s' % organization)
    if result_dict:
        message = _('Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                               't': time_format(end, use_l10n=True)}
    else:
        message = _('Unable to find a solution, maybe you should remove some constraints. '
                    'Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                               't': time_format(end, use_l10n=True)}
    Organization.objects.filter(pk=organization_id, celery_task_id=celery_id)\
        .update(celery_task_id=None, message=message)
