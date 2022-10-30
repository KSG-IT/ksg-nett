# Generated by Django 3.2.16 on 2022-10-25 18:05

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quotes", "0015_legacyquote"),
    ]

    operations = [
        migrations.AddField(
            model_name="quote",
            name="migrated_from_sg",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="quote",
            name="reported_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.DO_NOTHING,
                related_name="reported_quotes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]