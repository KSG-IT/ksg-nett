# Generated by Django 3.2.9 on 2021-12-22 23:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("summaries", "0005_alter_summary_summary_type"),
    ]

    operations = [
        migrations.RenameField(
            model_name="summary",
            old_name="summary_type",
            new_name="type",
        ),
    ]
