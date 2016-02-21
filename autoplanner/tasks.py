# -*- coding: utf-8 -*-

import celery
import datetime
from django.utils.formats import date_format, time_format
from django.utils.timezone import utc
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
    start = datetime.datetime.now(tz=utc)
    count = Organization.objects \
        .filter(pk=organization_id, celery_task_id=None) \
        .update(celery_task_id=celery_id, celery_start=start,
                message=_('Computation started at %(d)s, %(t)s') % {'d': date_format(start, use_l10n=True),
                                                                    't': time_format(start, use_l10n=True)})
    if count == 0:
        return
    organization = Organization.objects.get(pk=organization_id, celery_task_id=celery_id)
    scheduler = Scheduler(organization)
    result_list = scheduler.solve(verbose=False)
    result_dict = scheduler.result_by_agent(result_list)
    for agent_pk, task_pks in result_dict.items():
        Task.objects.filter(pk__in=task_pks, fixed=False, organization__id=organization_id).update(agent_id=agent_pk)
    end = datetime.datetime.now(tz=utc)
    if result_dict:
        message = _('Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                               't': time_format(end, use_l10n=True)}
    else:
        message = _('Unable to find a solution, maybe you should remove some constraints. '
                    'Computation finished at %(d)s, %(t)s') % {'d': date_format(end, use_l10n=True),
                                                               't': time_format(end, use_l10n=True)}
    Organization.objects.filter(pk=organization_id, celery_task_id=celery_id)\
        .update(celery_task_id=None, message=message)
