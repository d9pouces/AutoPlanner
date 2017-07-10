# Generated by Django 1.9.2 on 2016-02-17 19:35
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
                ('start_time', models.DateTimeField(blank=True, db_index=True, default=None, help_text='Before this date, the agent cannot performany task.', null=True, verbose_name='Arrival time')),
                ('end_time', models.DateTimeField(blank=True, db_index=True, default=None, help_text='After this date, the agent cannot perform any task.', null=True, verbose_name='Leaving time')),
            ],
        ),
        migrations.CreateModel(
            name='AgentCategoryPreferences',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('affinity', models.FloatField(blank=True, default=0.0, verbose_name='Affinity of the agent for the category.')),
                ('balancing_offset', models.FloatField(blank=True, default=0, verbose_name='Number of time units already done')),
                ('balancing_count', models.FloatField(blank=True, default=1.0, help_text='Blank if the agent cannot perform tasks of this category', null=True, verbose_name='If an agent should perform less tasks of this category,it should be > 1.0')),
                ('agent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Agent')),
            ],
        ),
        migrations.CreateModel(
            name='AgentTaskExclusion',
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
                ('balancing_mode', models.CharField(blank=True, choices=[(None, 'No balancing'), ('time', 'Total task time'), ('number', 'Total task number')], default=None, max_length=10, null=True, verbose_name='Balancing mode')),
                ('balancing_tolerance', models.FloatField(blank=True, default=None, null=True, verbose_name='Tolerance for balancing the total duration(s)|tasks across agents')),
                ('auto_affinity', models.FloatField(blank=True, default=0.0, verbose_name='Affinity for allocating successive tasks of the same category to the same agent')),
            ],
            options={
                'verbose_name': 'Category of tasks',
                'verbose_name_plural': 'Categories of tasks',
            },
        ),
        migrations.CreateModel(
            name='MaxTaskAffectation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(choices=[('min', 'At least this number of tasks'), ('max', 'At most this number of tasks')], default='max', max_length=3, verbose_name='Mode')),
                ('range_time_slice_days', models.IntegerField(default=2, verbose_name='Period length (days)')),
                ('range_time_slice_hours', models.IntegerField(default=0, verbose_name='Period length (hours)')),
                ('range_time_slice_seconds', models.IntegerField(default=0, verbose_name='Period length (seconds)')),
                ('task_maximum_count', models.IntegerField(default=1, verbose_name='Number of tasks in this range')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category')),
            ],
            options={
                'verbose_name': 'Number of tasks performed by an agent in a category',
                'verbose_name_plural': 'Number of tasks performed by an agent in a category',
            },
        ),
        migrations.CreateModel(
            name='MaxTimeTaskAffectation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mode', models.CharField(choices=[('min', 'At least this number of tasks'), ('max', 'At most this number of tasks')], default='max', max_length=3, verbose_name='Mode')),
                ('range_time_slice_days', models.IntegerField(default=2, verbose_name='Period length (days)')),
                ('range_time_slice_hours', models.IntegerField(default=0, verbose_name='Period length (hours)')),
                ('range_time_slice_seconds', models.IntegerField(default=0, verbose_name='Period length (seconds)')),
                ('task_maximum_time_days', models.IntegerField(default=1, verbose_name='Total task time in this range (days)')),
                ('task_maximum_time_hours', models.IntegerField(default=0, verbose_name='Total task time in this range (hours)')),
                ('task_maximum_time_seconds', models.IntegerField(default=0, verbose_name='Total task time in this range (seconds)')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category')),
            ],
            options={
                'verbose_name': 'Maximum time spent by an agent in a category',
                'verbose_name_plural': 'Maximum time spent by an agent in a category',
            },
        ),
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=500, verbose_name='Nom')),
                ('description', models.TextField(blank=True, default='', verbose_name='Description')),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(db_index=True, max_length=500, verbose_name='Nom')),
                ('start_time', models.DateTimeField(db_index=True, verbose_name='Start time')),
                ('end_time', models.DateTimeField(db_index=True, verbose_name='End time')),
                ('fixed', models.BooleanField(db_index=True, default=False, verbose_name='Agent is strongly fixed')),
                ('agent', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Agent')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Category')),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization')),
            ],
        ),
        migrations.AddField(
            model_name='maxtimetaskaffectation',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='maxtaskaffectation',
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
            model_name='agenttaskexclusion',
            name='organization',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Organization'),
        ),
        migrations.AddField(
            model_name='agenttaskexclusion',
            name='task',
            field=models.ForeignKey(help_text='Select the task that cannot be performed by the agent.', on_delete=django.db.models.deletion.CASCADE, to='autoplanner.Task', verbose_name='Task'),
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
