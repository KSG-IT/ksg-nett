# Generated by Django 2.1.2 on 2018-11-18 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0012_auto_20181118_2000'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='ksg_nickname',
            field=models.CharField(blank=True, max_length=20),
        ),
    ]