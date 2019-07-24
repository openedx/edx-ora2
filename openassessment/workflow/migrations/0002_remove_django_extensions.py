# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessmentworkflow',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True, db_index=True),
        ),
    ]
