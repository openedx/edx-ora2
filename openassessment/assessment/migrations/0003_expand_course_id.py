# -*- coding: utf-8 -*-
# pylint: skip-file
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0002_staffworkflow'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aiclassifierset',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='aigradingworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='aitrainingworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='peerworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='staffworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='studenttrainingworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
    ]
