# -*- coding: utf-8 -*-
# Generated by Django 1.11.2 on 2017-09-03 21:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autoplanner', '0002_auto_20170903_2258'),
    ]

    operations = [
        migrations.AlterField(
            model_name='schedulerun',
            name='celery_task_id',
            field=models.CharField(blank=True, db_index=True, default=None, max_length=60, null=True, verbose_name='Celery task id'),
        ),
    ]
