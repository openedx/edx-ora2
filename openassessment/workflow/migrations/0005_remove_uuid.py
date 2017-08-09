# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0004_reverse_gen_uuid'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='assessmentworkflow',
            name='uuid',
        ),
    ]
