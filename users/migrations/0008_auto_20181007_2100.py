# Generated by Django 2.1.2 on 2018-10-07 21:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20171116_1824'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='user',
            options={'default_related_name': 'users', 'verbose_name_plural': 'Users'},
        ),
        migrations.AlterField(
            model_name='user',
            name='last_name',
            field=models.CharField(blank=True, max_length=150, verbose_name='last name'),
        ),
    ]
