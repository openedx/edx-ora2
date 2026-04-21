from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0007_orareminder'),
    ]

    operations = [
        migrations.AddField(
            model_name='orareminder',
            name='last_known_step',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name='orareminder',
            name='step_start_time',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
