# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0003_expand_course_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='TrackChanges',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_submission_uuid', models.UUIDField(db_index=True, default=uuid.uuid4)),
                ('scorer_id', models.CharField(db_index=True, max_length=40)),
                ('json_edited_content', models.TextField(blank=True)),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='trackchanges',
            unique_together=set([('owner_submission_uuid', 'scorer_id')]),
        ),
    ]
