# Generated by Django 3.1.7 on 2021-03-03 19:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0014_auto_20201021_1453'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='ksg_role',
        ),
        migrations.RemoveField(
            model_name='user',
            name='ksg_status',
        ),
    ]
