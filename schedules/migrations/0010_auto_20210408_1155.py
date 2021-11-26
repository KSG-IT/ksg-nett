# Generated by Django 3.1.7 on 2021-04-08 11:55

from django.db import migrations, models
import django.db.models.deletion
import model_utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0009_auto_20190422_1627"),
    ]

    operations = [
        migrations.CreateModel(
            name="ShiftSlotGroupDayRule",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "rule",
                    model_utils.fields.StatusField(
                        choices=[
                            ("mo", "Monday"),
                            ("tu", "Tuesday"),
                            ("we", "Wednesday"),
                            ("th", "Thursday"),
                            ("fr", "Friday"),
                            ("sa", "Saturday"),
                            ("su", "Sunday"),
                            ("wk", "Weekdays"),
                            ("ed", "Weekends"),
                            ("fu", "Full weekends"),
                        ],
                        default="mo",
                        max_length=2,
                        no_check_for_status=True,
                    ),
                ),
                (
                    "shift_slot_group_template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="day_rules",
                        to="schedules.shiftslotgrouptemplate",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Shift slot group day rules",
                "unique_together": {("rule", "shift_slot_group_template")},
            },
        ),
        migrations.AlterField(
            model_name="schedule",
            name="name",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="scheduleslottype",
            name="role",
            field=models.CharField(
                choices=[
                    ("functionary", "Functionary"),
                    ("gang-member", "Gang member"),
                ],
                max_length=32,
            ),
        ),
        migrations.AlterField(
            model_name="shiftslot",
            name="group",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="shift_slots",
                to="schedules.shiftslotgroup",
            ),
        ),
        migrations.DeleteModel(
            name="ShiftSlotDayRule",
        ),
    ]