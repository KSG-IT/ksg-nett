# Generated by Django 3.1.2 on 2021-01-17 23:15

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0012_auto_20201204_2122'),
    ]

    operations = [
        migrations.AlterField(
            model_name='internalgrouppositionmembership',
            name='position',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='memberships', to='organization.internalgroupposition'),
        ),
    ]
