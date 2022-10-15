# Generated by Django 3.2.14 on 2022-10-12 16:35

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("economy", "0017_auto_20221012_1820"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="socisession",
            name="end",
        ),
        migrations.RemoveField(
            model_name="socisession",
            name="start",
        ),
        migrations.AddField(
            model_name="socisession",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="socisession",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
    ]