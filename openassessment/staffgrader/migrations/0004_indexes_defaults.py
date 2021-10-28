# Generated by Django 2.2.24 on 2021-10-28 15:26

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('staffgrader', '0003_lock_uuid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submissiongradinglock',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='submissiongradinglock',
            name='owner_id',
            field=models.CharField(max_length=40),
        ),
        migrations.AlterField(
            model_name='submissiongradinglock',
            name='submission_uuid',
            field=models.UUIDField(db_index=True, unique=True),
        ),
    ]
