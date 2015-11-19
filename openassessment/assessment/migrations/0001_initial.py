# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import django_extensions.db.fields
import openassessment.assessment.models.ai


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AIClassifier',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('classifier_data', models.FileField(upload_to=openassessment.assessment.models.ai.upload_to_path)),
            ],
        ),
        migrations.CreateModel(
            name='AIClassifierSet',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('algorithm_id', models.CharField(max_length=128, db_index=True)),
                ('course_id', models.CharField(max_length=40, db_index=True)),
                ('item_id', models.CharField(max_length=128, db_index=True)),
            ],
            options={
                'ordering': ['-created_at', '-id'],
            },
        ),
        migrations.CreateModel(
            name='AIGradingWorkflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', django_extensions.db.fields.UUIDField(db_index=True, unique=True, version=1, editable=False, blank=True)),
                ('course_id', models.CharField(max_length=40, db_index=True)),
                ('item_id', models.CharField(max_length=128, db_index=True)),
                ('scheduled_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('completed_at', models.DateTimeField(null=True, db_index=True)),
                ('algorithm_id', models.CharField(max_length=128, db_index=True)),
                ('submission_uuid', models.CharField(max_length=128, db_index=True)),
                ('essay_text', models.TextField(blank=True)),
                ('student_id', models.CharField(max_length=40, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='AITrainingWorkflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uuid', django_extensions.db.fields.UUIDField(db_index=True, unique=True, version=1, editable=False, blank=True)),
                ('course_id', models.CharField(max_length=40, db_index=True)),
                ('item_id', models.CharField(max_length=128, db_index=True)),
                ('scheduled_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('completed_at', models.DateTimeField(null=True, db_index=True)),
                ('algorithm_id', models.CharField(max_length=128, db_index=True)),
                ('classifier_set', models.ForeignKey(related_name='+', default=None, to='assessment.AIClassifierSet', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Assessment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('submission_uuid', models.CharField(max_length=128, db_index=True)),
                ('scored_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('scorer_id', models.CharField(max_length=40, db_index=True)),
                ('score_type', models.CharField(max_length=2)),
                ('feedback', models.TextField(default=b'', max_length=10000, blank=True)),
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
                ('feedback_text', models.TextField(default=b'', max_length=10000)),
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
                ('feedback', models.TextField(default=b'', blank=True)),
                ('assessment', models.ForeignKey(related_name='parts', to='assessment.Assessment')),
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
                ('criterion', models.ForeignKey(related_name='options', to='assessment.Criterion')),
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
                ('assessment', models.ForeignKey(to='assessment.Assessment', null=True)),
                ('author', models.ForeignKey(related_name='graded_by', to='assessment.PeerWorkflow')),
                ('scorer', models.ForeignKey(related_name='graded', to='assessment.PeerWorkflow')),
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
                ('rubric', models.ForeignKey(to='assessment.Rubric')),
            ],
        ),
        migrations.AddField(
            model_name='studenttrainingworkflowitem',
            name='training_example',
            field=models.ForeignKey(to='assessment.TrainingExample'),
        ),
        migrations.AddField(
            model_name='studenttrainingworkflowitem',
            name='workflow',
            field=models.ForeignKey(related_name='items', to='assessment.StudentTrainingWorkflow'),
        ),
        migrations.AddField(
            model_name='criterion',
            name='rubric',
            field=models.ForeignKey(related_name='criteria', to='assessment.Rubric'),
        ),
        migrations.AddField(
            model_name='assessmentpart',
            name='criterion',
            field=models.ForeignKey(related_name='+', to='assessment.Criterion'),
        ),
        migrations.AddField(
            model_name='assessmentpart',
            name='option',
            field=models.ForeignKey(related_name='+', to='assessment.CriterionOption', null=True),
        ),
        migrations.AddField(
            model_name='assessmentfeedback',
            name='options',
            field=models.ManyToManyField(default=None, related_name='assessment_feedback', to='assessment.AssessmentFeedbackOption'),
        ),
        migrations.AddField(
            model_name='assessment',
            name='rubric',
            field=models.ForeignKey(to='assessment.Rubric'),
        ),
        migrations.AddField(
            model_name='aitrainingworkflow',
            name='training_examples',
            field=models.ManyToManyField(related_name='+', to='assessment.TrainingExample'),
        ),
        migrations.AddField(
            model_name='aigradingworkflow',
            name='assessment',
            field=models.ForeignKey(related_name='+', default=None, to='assessment.Assessment', null=True),
        ),
        migrations.AddField(
            model_name='aigradingworkflow',
            name='classifier_set',
            field=models.ForeignKey(related_name='+', default=None, to='assessment.AIClassifierSet', null=True),
        ),
        migrations.AddField(
            model_name='aigradingworkflow',
            name='rubric',
            field=models.ForeignKey(related_name='+', to='assessment.Rubric'),
        ),
        migrations.AddField(
            model_name='aiclassifierset',
            name='rubric',
            field=models.ForeignKey(related_name='+', to='assessment.Rubric'),
        ),
        migrations.AddField(
            model_name='aiclassifier',
            name='classifier_set',
            field=models.ForeignKey(related_name='classifiers', to='assessment.AIClassifierSet'),
        ),
        migrations.AddField(
            model_name='aiclassifier',
            name='criterion',
            field=models.ForeignKey(related_name='+', to='assessment.Criterion'),
        ),
        migrations.AlterUniqueTogether(
            name='studenttrainingworkflowitem',
            unique_together=set([('workflow', 'order_num')]),
        ),
    ]
