# Generated by Django 3.2.14 on 2022-10-12 14:06

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0014_alter_productorder_purchased_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="productorder",
            name="cost",
            field=models.IntegerField(
                default=100,
                validators=[django.core.validators.MinValueValidator(limit_value=1)],
            ),
            preserve_default=False,
        ),
    ]
