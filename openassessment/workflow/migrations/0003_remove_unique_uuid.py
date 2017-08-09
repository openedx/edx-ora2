# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0002_remove_django_extensions'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessmentworkflow',
            name='uuid',
            field=models.UUIDField(default=None, null=True),
        ),
    ]
