# -*- coding: utf-8 -*-

from django.utils.translation import ugettext as _
from django.db import models
__author__ = 'Matthieu Gallet'


class Poll(models.Model):
    question = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def was_published_recently(self):
        return self.pub_date >= timezone.now() - datetime.timedelta(days=1)
    was_published_recently.admin_order_field = 'pub_date'
    was_published_recently.boolean = True
    was_published_recently.short_description = 'Published recently?'

    class Meta:
        verbose_name = _('poll')
        verbose_name_plural = _('polls')


class Choice(models.Model):
    poll = models.ForeignKey(Poll)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    class Meta:
        verbose_name = _('poll choice')
        verbose_name_plural = _('poll choices')



if __name__ == '__main__':
    import doctest
    doctest.testmod()