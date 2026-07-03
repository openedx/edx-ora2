from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('workflow', '0006_mariadb_uuid_conversion'),
    ]

    operations = [
        migrations.CreateModel(
            name='ORAReminder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('course_id', CourseKeyField(db_index=True, max_length=255)),
                ('ora_usage_key', UsageKeyField(max_length=255)),
                ('ora_name', models.CharField(default='', max_length=255)),
                ('submission_uuid', models.CharField(db_index=True, max_length=128, unique=True)),
                ('submission_time', models.DateTimeField()),
                ('content_url', models.TextField(blank=True, default='')),
                ('ora_due_date', models.DateTimeField(blank=True, null=True)),
                ('course_end_date', models.DateTimeField(blank=True, null=True)),
                ('peer_assessment_due', models.DateTimeField(blank=True, null=True)),
                ('self_assessment_due', models.DateTimeField(blank=True, null=True)),
                ('next_reminder_at', models.DateTimeField(blank=True, db_index=True, null=True)),
                ('is_active', models.BooleanField(db_index=True, default=False)),
                ('last_known_step', models.CharField(blank=True, max_length=32, null=True)),
                ('peer_must_be_graded_by', models.SmallIntegerField(default=1)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ora_reminders', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'indexes': [models.Index(fields=['is_active', 'next_reminder_at'], name='ora_reminder_sweep_idx')],
            },
        ),
    ]
