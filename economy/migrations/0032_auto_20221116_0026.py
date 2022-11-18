# Generated by Django 3.2.16 on 2022-11-15 23:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0031_deposit_migrated_from_sg"),
    ]

    operations = [
        migrations.RenameField(
            model_name="deposit",
            old_name="signed_off_time",
            new_name="approved_at",
        ),
        migrations.RenameField(
            model_name="deposit",
            old_name="signed_off_by",
            new_name="approved_by",
        ),
        migrations.RemoveField(
            model_name="deposit",
            name="migrated_from_sg",
        ),
    ]