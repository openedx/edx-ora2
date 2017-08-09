# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models, transaction
import uuid


def gen_uuid(apps, schema_editor):
    workflow_model_class = apps.get_model('workflow', 'AssessmentWorkflow')
    total_len = workflow_model_class.objects.count()
    current_index = 0
    chunk_size = 1000
    while current_index < total_len:
        end_chunk = current + chunk_size if total_len - chunk_size >= current_index else total_len
        with transaction.atomic():
            for workflow in workflow_model_class.objects.all()[current_index:end_chunk].iterator():
                workflow.uuid = uuid.uuid4()
                workflow.save()
        current_index = current_index + chunk_size


class Migration(migrations.Migration):
    """
    If we want to undo the "remove uuid field" operation, we must do so in
    multiple migrations to deal with the field being unique and non null.

    https://docs.djangoproject.com/en/1.9/howto/writing-migrations/#migrations-that-add-unique-fields
    """

    dependencies = [
        ('workflow', '0003_remove_unique_uuid'),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop, reverse_code=gen_uuid)
    ]
