# Generated by Django 3.2.12 on 2022-03-15 19:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('schedules', '0013_alter_usershift_role'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='newshift',
            name='contact_person',
        ),
    ]
