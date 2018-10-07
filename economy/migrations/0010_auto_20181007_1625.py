# Generated by Django 2.1.2 on 2018-10-07 16:25

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('economy', '0009_auto_20181001_1925'),
    ]

    operations = [
        migrations.AlterField(
            model_name='deposit',
            name='signed_off_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='verified_deposits', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='productorder',
            name='amount',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='purchase',
            name='signed_off_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='verified_purchases', to=settings.AUTH_USER_MODEL),
        ),
    ]
