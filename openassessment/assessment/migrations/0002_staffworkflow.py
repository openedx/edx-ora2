# -*- coding: utf-8 -*-
# pylint: skip-file


from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StaffWorkflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('scorer_id', models.CharField(max_length=40, db_index=True)),
                ('course_id', models.CharField(max_length=40, db_index=True)),
                ('item_id', models.CharField(max_length=128, db_index=True)),
                ('submission_uuid', models.CharField(unique=True, max_length=128, db_index=True)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, db_index=True)),
                ('grading_completed_at', models.DateTimeField(null=True, db_index=True)),
                ('grading_started_at', models.DateTimeField(null=True, db_index=True)),
                ('cancelled_at', models.DateTimeField(null=True, db_index=True)),
                ('assessment', models.CharField(max_length=128, null=True, db_index=True)),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
