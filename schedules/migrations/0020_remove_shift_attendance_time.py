# Generated by Django 3.2.12 on 2022-03-28 20:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0019_auto_20220322_2128'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='shift',
            name='attendance_time',
        ),
    ]