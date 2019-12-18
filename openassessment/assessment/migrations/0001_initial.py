# -*- coding: utf-8 -*-
# pylint: skip-file
from __future__ import absolute_import, unicode_literals

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Assessment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_uuid', models.CharField(max_length=128, db_index=True)),
                ('scored_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('scorer_id', models.CharField(max_length=40, db_index=True)),
                ('score_type', models.CharField(max_length=2)),
                ('feedback', models.TextField(default=u'', max_length=10000, blank=True)),
            ],
            options={
                'ordering': ['-scored_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='AssessmentFeedback',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_uuid', models.CharField(unique=True, max_length=128, db_index=True)),
                ('feedback_text', models.TextField(default=u'', max_length=10000)),
                ('assessments', models.ManyToManyField(default=None, related_name='assessment_feedback', to='assessment.Assessment')),
            ],
        ),
        migrations.CreateModel(
            name='AssessmentFeedbackOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('text', models.CharField(unique=True, max_length=255)),
            ],
        ),
        migrations.CreateModel(
            name='AssessmentPart',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('feedback', models.TextField(default=u'', blank=True)),
                ('assessment', models.ForeignKey(related_name='parts', to='assessment.Assessment', on_delete=models.CASCADE)),
            ],
        ),
        migrations.CreateModel(
            name='Criterion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=100, blank=True)),
                ('order_num', models.PositiveIntegerField()),
                ('prompt', models.TextField(max_length=10000)),
            ],
            options={
                'ordering': ['rubric', 'order_num'],
            },
        ),
        migrations.CreateModel(
            name='CriterionOption',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order_num', models.PositiveIntegerField()),
                ('points', models.PositiveIntegerField()),
                ('name', models.CharField(max_length=100)),
                ('label', models.CharField(max_length=100, blank=True)),
                ('explanation', models.TextField(max_length=10000, blank=True)),
                ('criterion', models.ForeignKey(related_name='options', to='assessment.Criterion', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['criterion', 'order_num'],
            },
        ),
        migrations.CreateModel(
            name='PeerWorkflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('student_id', models.CharField(max_length=40, db_index=True)),
                ('item_id', models.CharField(max_length=128, db_index=True)),
                ('course_id', models.CharField(max_length=40, db_index=True)),
                ('submission_uuid', models.CharField(unique=True, max_length=128, db_index=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('completed_at', models.DateTimeField(null=True, db_index=True)),
                ('grading_completed_at', models.DateTimeField(null=True, db_index=True)),
                ('cancelled_at', models.DateTimeField(null=True, db_index=True)),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='PeerWorkflowItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_uuid', models.CharField(max_length=128, db_index=True)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('scored', models.BooleanField(default=False)),
                ('assessment', models.ForeignKey(to='assessment.Assessment', null=True, on_delete=models.CASCADE)),
                ('author', models.ForeignKey(related_name='graded_by', to='assessment.PeerWorkflow', on_delete=models.CASCADE)),
                ('scorer', models.ForeignKey(related_name='graded', to='assessment.PeerWorkflow', on_delete=models.CASCADE)),
            ],
            options={
                'ordering': ['started_at', 'id'],
            },
        ),
        migrations.CreateModel(
            name='Rubric',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('content_hash', models.CharField(unique=True, max_length=40, db_index=True)),
                ('structure_hash', models.CharField(max_length=40, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudentTrainingWorkflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_uuid', models.CharField(unique=True, max_length=128, db_index=True)),
                ('student_id', models.CharField(max_length=40, db_index=True)),
                ('item_id', models.CharField(max_length=128, db_index=True)),
                ('course_id', models.CharField(max_length=40, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='StudentTrainingWorkflowItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('order_num', models.PositiveIntegerField()),
                ('started_at', models.DateTimeField(auto_now_add=True)),
                ('completed_at', models.DateTimeField(default=None, null=True)),
            ],
            options={
                'ordering': ['workflow', 'order_num'],
            },
        ),
        migrations.CreateModel(
            name='TrainingExample',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('raw_answer', models.TextField(blank=True)),
                ('content_hash', models.CharField(unique=True, max_length=40, db_index=True)),
                ('options_selected', models.ManyToManyField(to='assessment.CriterionOption')),
                ('rubric', models.ForeignKey(to='assessment.Rubric', on_delete=models.CASCADE)),
            ],
        ),
        migrations.AddField(
            model_name='studenttrainingworkflowitem',
            name='training_example',
            field=models.ForeignKey(to='assessment.TrainingExample', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='studenttrainingworkflowitem',
            name='workflow',
            field=models.ForeignKey(related_name='items', to='assessment.StudentTrainingWorkflow', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='criterion',
            name='rubric',
            field=models.ForeignKey(related_name='criteria', to='assessment.Rubric', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='assessmentpart',
            name='criterion',
            field=models.ForeignKey(related_name='+', to='assessment.Criterion', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='assessmentpart',
            name='option',
            field=models.ForeignKey(related_name='+', to='assessment.CriterionOption', null=True, on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='assessmentfeedback',
            name='options',
            field=models.ManyToManyField(default=None, related_name='assessment_feedback', to='assessment.AssessmentFeedbackOption'),
        ),
        migrations.AddField(
            model_name='assessment',
            name='rubric',
            field=models.ForeignKey(to='assessment.Rubric', on_delete=models.CASCADE),
        ),
        migrations.AlterUniqueTogether(
            name='studenttrainingworkflowitem',
            unique_together=set([('workflow', 'order_num')]),
        ),
    ]
