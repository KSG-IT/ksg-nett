# Generated by Django 2.1.2 on 2018-11-05 20:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_remove_user_balance'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='hide_relationship_status',
            field=models.BooleanField(default=False),
        ),
    ]
