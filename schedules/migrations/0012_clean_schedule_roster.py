from django.db import migrations


def clean_schedule_roster(apps, schema_editor):
    """
    Prepare for a required autofill_as and one row per user and schedule.
    A row without a role gets the default role of the schedule, or is deleted.
    Of duplicate rows, the oldest row stays.
    """
    ScheduleRoster = apps.get_model("schedules", "ScheduleRoster")

    for row in ScheduleRoster.objects.filter(autofill_as__isnull=True).select_related(
        "schedule"
    ):
        if row.schedule.default_role:
            row.autofill_as = row.schedule.default_role
            row.save(update_fields=["autofill_as"])
        else:
            row.delete()

    seen = set()
    for row in ScheduleRoster.objects.order_by("id"):
        key = (row.schedule_id, row.user_id)
        if key in seen:
            row.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0011_roster_groupings"),
    ]

    operations = [
        migrations.RunPython(clean_schedule_roster, migrations.RunPython.noop),
    ]
