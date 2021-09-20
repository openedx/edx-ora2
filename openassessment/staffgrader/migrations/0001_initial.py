# Generated by Django 2.2.24 on 2021-09-14 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SubmissionGradingLock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('owner_id', models.CharField(db_index=True, max_length=40)),
                ('created_at', models.DateTimeField(db_index=True, null=True)),
                ('submission_uuid', models.CharField(db_index=True, max_length=128, unique=True)),
                ('submission_type', models.CharField(choices=[('INDV', 'Individual'), ('TEAM', 'Team')], max_length=4)),
            ],
            options={
                'ordering': ['created_at', 'id'],
            },
        ),
    ]
