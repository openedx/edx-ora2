# Generated by Django 2.2.24 on 2021-10-26 16:52

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('staffgrader', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submissiongradinglock',
            name='created_at',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
    ]
