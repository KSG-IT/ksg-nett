# Generated by Django 3.2.11 on 2022-01-30 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("organization", "0022_auto_20210303_1939"),
    ]

    operations = [
        migrations.AddField(
            model_name="internalgrouppositionmembership",
            name="type",
            field=models.CharField(
                choices=[
                    ("functionary", "Functionary"),
                    ("active-functionary-pang", "Active functionary pang"),
                    ("old-functionary-pang", "Old functionary pang"),
                    ("gang-member", "Gang member"),
                    ("active-gang-member-pang", "Active gang member pang"),
                    ("old-gang-member-pang", "Old gang member pang"),
                    ("interest-group-member", "Interest group member"),
                    ("hangaround", "Hangaround"),
                    ("temporary-leave", "Temporary leave"),
                ],
                default="gang-member",
                max_length=32,
            ),
            preserve_default=False,
        ),
        migrations.AlterUniqueTogether(
            name="internalgroupposition",
            unique_together={("name", "internal_group")},
        ),
        migrations.RemoveField(
            model_name="internalgroupposition",
            name="type",
        ),
    ]
