# Generated by Django 2.1.5 on 2019-02-01 15:52

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SensorMeasurement',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('temperature', 'Temperature'), ('humidity', 'Humidity'), ('sound', 'Sound')], max_length=16)),
                ('value', models.FloatField()),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
            ],
        ),
        migrations.AddIndex(
            model_name='sensormeasurement',
            index=models.Index(fields=['created_at'], name='sensors_sen_created_89d580_idx'),
        ),
    ]
