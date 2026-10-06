from django.db import migrations


def dedupe_shift_interest(apps, schema_editor):
    """
    Prepare for one answer per user and shift. Of duplicate rows, the newest
    row stays, because it is the last answer of the user.
    """
    ShiftInterest = apps.get_model("schedules", "ShiftInterest")

    seen = set()
    for interest in ShiftInterest.objects.order_by("-created_at", "-id"):
        key = (interest.shift_id, interest.user_id)
        if key in seen:
            interest.delete()
        else:
            seen.add(key)


class Migration(migrations.Migration):

    dependencies = [
        ("schedules", "0014_planning_period"),
    ]

    operations = [
        migrations.RunPython(dedupe_shift_interest, migrations.RunPython.noop),
    ]
