# Generated by Django 3.1.2 on 2020-12-05 16:37

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('economy', '0005_auto_20201107_1029'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productorder',
            name='order_size',
            field=models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(limit_value=1)]),
        ),
    ]
