# Generated by Django 3.2.5 on 2021-11-26 15:02

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('quiz', '0008_alter_participant_quiz'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='participant',
            name='guessed',
        ),
        migrations.RemoveField(
            model_name='quiz',
            name='identifier',
        ),
        migrations.RemoveField(
            model_name='quiz',
            name='quiz_choices',
        ),
        migrations.RemoveField(
            model_name='quiz',
            name='quiz_pick',
        ),
        migrations.AddField(
            model_name='quiz',
            name='participant',
            field=models.ManyToManyField(blank=True, related_name='quiz_participants', through='quiz.Participant', to=settings.AUTH_USER_MODEL),
        ),
    ]
