# Generated by Django 3.1.2 on 2021-02-04 14:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0016_auto_20210117_2330'),
    ]

    operations = [
        migrations.AddField(
            model_name='internalgroup',
            name='group_image',
            field=models.ImageField(blank=True, null=True, upload_to='internalgroups'),
        ),
    ]