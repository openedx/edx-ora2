# -*- coding: utf-8 -*-
# pylint: skip-file


from django.db import migrations, models
import django.utils.timezone

import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AssessmentWorkflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, verbose_name='created', editable=False)),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, verbose_name='modified', editable=False)),
                ('status', model_utils.fields.StatusField(default=u'peer', max_length=100, verbose_name='status', no_check_for_status=True, choices=[(u'peer', u'peer'), (u'ai', u'ai'), (u'self', u'self'), (u'training', u'training'), (u'waiting', u'waiting'), (u'done', u'done'), (u'cancelled', u'cancelled')])),
                ('status_changed', model_utils.fields.MonitorField(default=django.utils.timezone.now, verbose_name='status changed', monitor='status')),
                ('submission_uuid', models.CharField(unique=True, max_length=36, db_index=True)),
                ('uuid', models.UUIDField(db_index=True, unique=True, editable=False, blank=True)),
                ('course_id', models.CharField(max_length=255, db_index=True)),
                ('item_id', models.CharField(max_length=255, db_index=True)),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='AssessmentWorkflowCancellation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('comments', models.TextField(max_length=10000)),
                ('cancelled_by_id', models.CharField(max_length=40, db_index=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('workflow', models.ForeignKey(related_name='cancellations', to='workflow.AssessmentWorkflow', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='AssessmentWorkflowStep',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=20)),
                ('submitter_completed_at', models.DateTimeField(default=None, null=True)),
                ('assessment_completed_at', models.DateTimeField(default=None, null=True)),
                ('order_num', models.PositiveIntegerField()),
                ('workflow', models.ForeignKey(related_name='steps', to='workflow.AssessmentWorkflow', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['workflow', 'order_num'],
            },
        ),
    ]
