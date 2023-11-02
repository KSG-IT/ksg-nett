# Generated by Django 4.2.3 on 2023-10-26 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0002_socisession_minimum_remaining_balance"),
    ]

    operations = [
        migrations.AddField(
            model_name="sociproduct",
            name="purchase_price",
            field=models.IntegerField(
                blank=True,
                help_text="What the product is valued when purchasing it for inventory",
                null=True,
            ),
        ),
    ]