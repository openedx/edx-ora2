# Generated by Django 2.2.19 on 2021-05-18 21:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0006_TeamWorkflows'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assessmentpart',
            name='feedback',
            field=models.TextField(blank=True, default='', max_length=102400),
        ),
    ]
