# Generated by Django 3.2.18 on 2023-03-07 14:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0006_externalcharge"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="socisession",
            options={"permissions": [("can_overcharge", "Can overcharge")]},
        ),
    ]