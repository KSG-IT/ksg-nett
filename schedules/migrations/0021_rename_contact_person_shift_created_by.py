# Generated by Django 3.2.12 on 2022-03-28 20:32

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0020_remove_shift_attendance_time'),
    ]

    operations = [
        migrations.RenameField(
            model_name='shift',
            old_name='contact_person',
            new_name='created_by',
        ),
    ]