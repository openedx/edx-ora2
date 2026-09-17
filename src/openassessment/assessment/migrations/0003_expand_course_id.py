# pylint: skip-file


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('assessment', '0002_staffworkflow'),
    ]

    operations = [
        migrations.AlterField(
            model_name='peerworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='staffworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
        migrations.AlterField(
            model_name='studenttrainingworkflow',
            name='course_id',
            field=models.CharField(max_length=255, db_index=True),
        ),
    ]
