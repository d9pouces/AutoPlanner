import datetime
import random

from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.http import HttpRequest
from django.urls import reverse
from django.utils.formats import date_format, time_format
from django.utils.text import force_text
from django.utils.timezone import get_default_timezone
from django.utils.translation import ugettext_lazy as _

API_KEY_VARIABLE = 'api_key'

__author__ = 'Matthieu Gallet'


def default_day_start():
    x = datetime.datetime.now(tz=get_default_timezone())
    return datetime.datetime(year=x.year, month=x.month, day=x.day, hour=0, minute=0, second=0,
                             tzinfo=get_default_timezone())


def default_day_end():
    return default_day_start() + datetime.timedelta(hours=23, minutes=59, seconds=59)


def default_token(length=64, allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                           'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    # noinspection PyUnusedLocal
    return ''.join([random.choice(allowed_chars) for i in range(length)])


class Organization(models.Model):
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    message = models.CharField(_('Message'), blank=True, max_length=500, default='')
    description = models.TextField(_('Description'), default='', blank=True)
    celery_task_id = models.CharField(_('Celery task id'), db_index=True, max_length=20, blank=True, null=True,
                                      default=None)
    celery_start = models.DateTimeField(_('Celery start'), null=True, blank=True, default=None)
    celery_end = models.DateTimeField(_('Celery end'), null=True, blank=True, default=None)
    access_token = models.CharField(_('Access token'), default=default_token, max_length=300,
                                    validators=[RegexValidator(r'^[a-zA-Z0-9]{1,300}$')])
    max_compute_time = models.PositiveIntegerField(_('Maximum time, in seconds, for finding a solution'),
                                                   default=None, blank=True, null=True,
                                                   help_text=_('Leave it blank if you do not want to set a limit'))
    admins = models.ManyToManyField(settings.AUTH_USER_MODEL, db_index=True, verbose_name=_('Administrators'))
    current_schedule = models.ForeignKey('ScheduleRun', default=None, blank=True, null=True, db_index=True,
                                         related_name='current_organizations', on_delete=models.CASCADE)

    @classmethod
    def query(cls, request: HttpRequest, readonly=False):
        return cls.objects.all()
        # noinspection PyUnresolvedReferences
        if request.user.is_anonymous:
            return cls.objects.filter(access_token=request.GET.get(API_KEY_VARIABLE, ''))
        # noinspection PyUnresolvedReferences
        if request.user.is_superuser:
            return cls.objects.all()
        if readonly:
            # noinspection PyUnresolvedReferences
            return cls.objects.filter(Q(admins=request.user) | Q(access_token=request.GET.get(API_KEY_VARIABLE, '')))
        # noinspection PyUnresolvedReferences
        return cls.objects.filter(admins=request.user)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return '%s?%s=%s' % (reverse('organization', kwargs={'organization_pk': self.pk}),
                             API_KEY_VARIABLE, self.access_token)


class ScheduleRun(models.Model):
    organization = models.ForeignKey(Organization, db_index=True, on_delete=models.CASCADE)
    status = models.NullBooleanField(_('Is valid?'), db_index=True, default=None)
    is_selected = models.BooleanField(_('Selected?'), db_index=True, default=False)
    message = models.TextField(_('Result'), max_length=500, default='', blank=True)
    celery_task_id = models.CharField(_('Celery task id'), db_index=True, max_length=20, blank=True, null=True,
                                      default=None)
    celery_start = models.DateTimeField(_('Computation start'), null=True, blank=True, default=None)
    celery_end = models.DateTimeField(_('Computation end'), null=True, blank=True, default=None)
    process_id = models.IntegerField(_('Process ID'), db_index=True, blank=True, null=True, default=None)
    result_dict = models.TextField(_('JSON-serialized result'), blank=True, default=None, null=True)

    def __str__(self):
        end = self.celery_end
        if not end:
            return force_text(_('Not finished yet.'))
        return '%(d)s, %(t)s' % {'d': date_format(end, use_l10n=True), 't': time_format(end, use_l10n=True)}

    def __unicode__(self):
        return self.__str__()


class OrganizationObject(models.Model):
    organization = models.ForeignKey(Organization, db_index=True, on_delete=models.CASCADE)

    class Meta(object):
        abstract = True

    @classmethod
    def query(cls, request: HttpRequest):
        # noinspection PyUnresolvedReferences
        if request.user.is_superuser:
            return cls.objects.all()
        # noinspection PyUnresolvedReferences
        return cls.objects.filter(organization__admins=request.user)


class Agent(OrganizationObject):
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time = models.DateTimeField(_('Arrival time'), db_index=True, default=None, blank=True, null=True,
                                      help_text=_('Before this date, the agent cannot perform'
                                                  'any task.'))
    end_time = models.DateTimeField(_('Leaving time'), db_index=True, default=None, blank=True, null=True,
                                    help_text=_('After this date, the agent cannot perform any task.'))

    class Meta(object):
        ordering = ('name',)

    def __str__(self):
        return self.name


class Category(OrganizationObject):
    BALANCE_TIME = 'time'
    BALANCE_NUMBER = 'number'
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    balancing_mode = models.CharField(_('Balancing mode'),
                                      max_length=10, choices=((None, _('No balancing')),
                                                              (BALANCE_TIME, _('Total task time')),
                                                              (BALANCE_NUMBER, _('Total task number'))),
                                      blank=True, null=True, default=None)
    balancing_tolerance = models.FloatField(_('Tolerance for balancing the total duration (in seconds)|tasks '
                                              'across agents'), default=0., blank=True, null=True)
    auto_affinity = models.FloatField(_('Affinity for allocating successive tasks of the same category '
                                        'to the same agent'), default=0., blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _('Category of tasks')
        verbose_name_plural = _('Categories of tasks')

    @property
    def balancing_tolerance_as_timedelta_2(self):
        return datetime.timedelta(seconds=(self.balancing_tolerance or 0) * 2.)

    @property
    def balancing_tolerance_2(self):
        return (self.balancing_tolerance or 0) * 2.


class MaxAffectation(OrganizationObject):
    MINIMUM = 'min'
    MAXIMUM = 'max'
    category = models.ForeignKey(Category, db_index=True, on_delete=models.CASCADE)
    mode = models.CharField(_('Mode'), max_length=3, choices=((MINIMUM, _('At least this number of tasks')),
                                                              (MAXIMUM, _('At most this number of tasks'))),
                            default=MAXIMUM)
    range_time_slice_days = models.IntegerField(_('Period length (days)'), default=2)
    range_time_slice_hours = models.IntegerField(_('Period length (hours)'), default=0)
    range_time_slice_seconds = models.IntegerField(_('Period length (seconds)'), default=0)

    @property
    def range_time_slice(self):
        return datetime.timedelta(days=self.range_time_slice_days, hours=self.range_time_slice_hours,
                                  seconds=self.range_time_slice_seconds)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.organization_id is None and self.category_id:
            self.organization_id = self.category.organization_id
        super().save(force_insert=force_insert, force_update=force_update, using=using,
                     update_fields=update_fields)

    class Meta:
        abstract = True


class MaxTaskAffectation(MaxAffectation):
    task_maximum_count = models.IntegerField(_('Number of tasks in this range'), default=1)

    class Meta:
        verbose_name = _('Number of tasks performed by an agent in a category')
        verbose_name_plural = _('Number of tasks performed by an agent in a category')


class MaxTimeTaskAffectation(MaxAffectation):
    task_maximum_time_days = models.IntegerField(_('Total task time in this range (days)'), default=1)
    task_maximum_time_hours = models.IntegerField(_('Total task time in this range (hours)'), default=0)
    task_maximum_time_seconds = models.IntegerField(_('Total task time in this range (seconds)'), default=0)

    @property
    def task_maximum_time(self):
        return datetime.timedelta(days=self.task_maximum_time_days, hours=self.task_maximum_time_hours,
                                  seconds=self.task_maximum_time_seconds)

    class Meta:
        verbose_name = _('Maximum time spent by an agent in a category')
        verbose_name_plural = _('Maximum time spent by an agent in a category')


class Task(OrganizationObject):
    orders = {'name', '-name', 'start_time', '-start_time', 'end_time', '-end_time'}
    categories = models.ManyToManyField(Category, db_index=True, blank=True)
    name = models.CharField(_('Name'), db_index=True, max_length=500)
    start_time = models.DateTimeField(_('Start time'), db_index=True, default=default_day_start)
    end_time = models.DateTimeField(_('End time'), db_index=True, default=default_day_end)
    agent = models.ForeignKey(Agent, db_index=True, null=True, default=None, blank=True, on_delete=models.SET_NULL)
    fixed = models.BooleanField(_('Forced agent'), db_index=True, default=False)
    task_serie = models.ForeignKey('self', db_index=True, null=True, default=None, on_delete=models.SET_NULL,
                                   blank=True)

    class Meta(object):
        ordering = ('start_time', 'end_time',)

    @property
    def duration(self) -> datetime.timedelta:
        return self.end_time - self.start_time

    def __str__(self):
        start = date_format(self.start_time, use_l10n=True)
        end = date_format(self.end_time, use_l10n=True)
        return '%s (%s -> %s)' % (self.name, start, end)


class AgentCategoryPreferences(OrganizationObject):
    category = models.ForeignKey(Category, db_index=True, on_delete=models.CASCADE)
    agent = models.ForeignKey(Agent, db_index=True, on_delete=models.CASCADE)
    affinity = models.FloatField(_('Affinity of the agent for the category.'), default=0., blank=True)
    balancing_offset = models.FloatField(_('Number of time units already done'), default=0, blank=True)
    balancing_count = models.FloatField(_('If a task of this category performed by this agent counts twice, '
                                          'set this number to 2.0.'),
                                        default=1.0, blank=True, null=True,
                                        help_text=_('Blank if the agent cannot perform tasks of this category'))

    class Meta(object):
        verbose_name = 'preference by agent and category'
        verbose_name_plural = 'preferences by agent and category'

    @property
    def offset_as_timedelta(self):
        return datetime.timedelta(seconds=self.balancing_offset)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.organization_id is None and self.category_id:
            self.organization_id = self.category.organization_id
        elif self.organization_id is None and self.agent_id:
            self.organization_id = self.agent.organization_id
        super().save(force_insert=force_insert, force_update=force_update, using=using,
                     update_fields=update_fields)


class AgentTaskExclusion(OrganizationObject):
    agent = models.ForeignKey(Agent, db_index=True, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, db_index=True, verbose_name=_('Task'), on_delete=models.CASCADE,
                             help_text=_('Select the task that cannot be performed by the agent.'))

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        if self.organization_id is None and self.task_id:
            self.organization_id = self.task.organization_id
        elif self.organization_id is None and self.agent_id:
            self.organization_id = self.agent.organization_id
        super().save(force_insert=force_insert, force_update=force_update, using=using,
                     update_fields=update_fields)
