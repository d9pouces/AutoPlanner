# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-20 10:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('autoplanner', '0002_auto_20160219_2251'),
    ]

    operations = [
        migrations.AddField(
            model_name='organization',
            name='message',
            field=models.CharField(blank=True, default='', max_length=500, verbose_name='Message'),
        ),
    ]
