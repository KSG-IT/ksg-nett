# Generated by Django 3.2.11 on 2022-01-23 17:53

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("quotes", "0012_auto_20211202_1347"),
    ]

    operations = [
        migrations.AlterField(
            model_name="quotevote",
            name="caster",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="quote_votes",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
