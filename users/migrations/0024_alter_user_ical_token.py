# Generated by Django 3.2.16 on 2022-11-03 13:01

from django.db import migrations, models
from users.utils import ical_token_generator


class Migration(migrations.Migration):
    def generate_ical_token(apps, schema_editor):
        User = apps.get_model("users", "User")
        for user in User.objects.all():
            user.ical_token = ical_token_generator()
            user.save()

    dependencies = [
        ("users", "0023_alter_user_ical_token"),
    ]

    operations = [
        migrations.RunPython(generate_ical_token, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="user",
            name="ical_token",
            field=models.CharField(
                default=ical_token_generator, max_length=128, unique=True
            ),
        ),
    ]
