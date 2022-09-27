# Generated by Django 3.2.13 on 2022-09-12 22:12

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0025_remove_shift_created_by"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="shiftslot",
            options={"verbose_name_plural": "Shift slots"},
        ),
        migrations.AlterField(
            model_name="shiftslot",
            name="shift",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="slots",
                to="schedules.shift",
            ),
        ),
    ]