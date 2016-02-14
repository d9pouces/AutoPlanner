# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-02-13 21:39
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Agent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=500, verbose_name='Nom')),
                ('start_time_slice', models.IntegerField(blank=True, db_index=True, default=0, verbose_name='Arrival time slice')),
                ('end_time_slice', models.IntegerField(blank=True, db_index=True, default=1, verbose_name='Leaving time slice')),
            ],
        ),
        migrations.CreateModel(
            name='AgentCategoryPreferences',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('affinity', models.FloatField(blank=True, default=0.0, verbose_name='Affinity of the agent for the category.')),
                ('balancing_offset', models.FloatField(blank=True, default=0, verbose_name='Number of time units already done')),
                ('balancing_count', models.FloatField(blank=True, default=1.0, help_text='Blank if the agent cannot perform events of this category', null=True, verbose_name='If an agent should perform less events of this category,it should be > 1.0')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Agent')),
            ],
        ),
        migrations.CreateModel(
            name='AgentEventExclusion',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Agent')),
            ],
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=500, verbose_name='Nom')),
                ('balancing_mode', models.CharField(blank=True, choices=[(None, 'No balancing'), ('time', 'Total event time'), ('number', 'Total event number')], default=None, max_length=10, null=True, verbose_name='Balancing mode')),
                ('balancing_tolerance', models.FloatField(blank=True, default=1.0, verbose_name='Tolerance for balancing the total duration across agents')),
                ('auto_affinity', models.FloatField(blank=True, default=0.0, verbose_name='Affinity for allocating successive events of the same category to the same agent')),
            ],
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=500, verbose_name='Nom')),
                ('start_time_slice', models.IntegerField(db_index=True, verbose_name='Start time')),
                ('end_time_slice', models.IntegerField(blank=True, db_index=True, default=None, null=True, verbose_name='End time')),
                ('fixed', models.BooleanField(db_index=True, default=False, verbose_name='Agent is strongly fixed')),
                ('agent', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Agent')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category')),
            ],
        ),
        migrations.CreateModel(
            name='MaxEventAffectation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('range_time_slice', models.IntegerField(default=2, verbose_name='Period length (in time units)')),
                ('event_maximum_count', models.IntegerField(default=1, verbose_name='Maximum number of events in this range')),
                ('event_maximum_duration', models.BooleanField(default=False, verbose_name='Use event durations')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category')),
            ],
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=500, verbose_name='Nom')),
                ('time_slice_duration', models.IntegerField(default=86400, verbose_name='Time slice duration (s)')),
                ('time_slice_offset', models.IntegerField(blank=True, default=0, verbose_name='Starting time slice')),
            ],
        ),
        migrations.AddField(
            model_name='maxeventaffectation',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='event',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='category',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='category',
            name='parent_category',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category', verbose_name='Parent category'),
        ),
        migrations.AddField(
            model_name='agenteventexclusion',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Event'),
        ),
        migrations.AddField(
            model_name='agenteventexclusion',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='agentcategorypreferences',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category'),
        ),
        migrations.AddField(
            model_name='agentcategorypreferences',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='agent',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
    ]