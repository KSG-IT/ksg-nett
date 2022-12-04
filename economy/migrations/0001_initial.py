# Generated by Django 3.2.16 on 2022-12-04 20:24

import datetime
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import economy.models
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Deposit",
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
                ("created_at", models.DateTimeField(default=datetime.datetime.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("description", models.TextField(blank=True, default="")),
                ("amount", models.IntegerField()),
                (
                    "receipt",
                    models.ImageField(
                        blank=True,
                        default=None,
                        null=True,
                        upload_to=economy.models.Deposit._receipt_upload_location,
                    ),
                ),
                ("approved", models.BooleanField(default=False)),
                (
                    "approved_at",
                    models.DateTimeField(blank=True, default=None, null=True),
                ),
            ],
            options={
                "permissions": (
                    ("approve_deposit", "Can approve deposits"),
                    ("invalidate_deposit", "Can invalidate deposits"),
                ),
            },
        ),
        migrations.CreateModel(
            name="DepositComment",
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
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                ("comment", models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name="ProductOrder",
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
                    "order_size",
                    models.IntegerField(
                        default=1,
                        validators=[
                            django.core.validators.MinValueValidator(limit_value=1)
                        ],
                    ),
                ),
                ("purchased_at", models.DateTimeField(auto_now_add=True)),
                (
                    "cost",
                    models.IntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(limit_value=1)
                        ]
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SociBankAccount",
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
                ("balance", models.IntegerField(default=0, editable=False)),
                (
                    "card_uuid",
                    models.CharField(blank=True, max_length=50, null=True, unique=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SociOrderSession",
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
                    "status",
                    models.CharField(
                        choices=[
                            ("CREATED", "Created"),
                            ("FOOD_ORDERING", "Food Ordering"),
                            ("DRINK_ORDERING", "Drink Ordering"),
                            ("CLOSED", "Closed"),
                        ],
                        default="CREATED",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "order_pdf",
                    models.FileField(
                        blank=True, null=True, upload_to="soci_order_sessions"
                    ),
                ),
            ],
            options={
                "verbose_name": "Soci Order Session",
                "verbose_name_plural": "Soci Order Sessions",
            },
        ),
        migrations.CreateModel(
            name="SociOrderSessionOrder",
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
                ("amount", models.IntegerField()),
                ("ordered_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Soci Order Session Order",
                "verbose_name_plural": "Soci Order Session Orders",
            },
        ),
        migrations.CreateModel(
            name="SociProduct",
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
                    "start",
                    models.DateTimeField(blank=True, null=True, verbose_name="start"),
                ),
                (
                    "end",
                    models.DateTimeField(blank=True, null=True, verbose_name="end"),
                ),
                (
                    "type",
                    models.CharField(
                        choices=[("FOOD", "Food"), ("DRINK", "Drink")],
                        max_length=10,
                        null=True,
                    ),
                ),
                (
                    "sku_number",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="Product SKU number"
                    ),
                ),
                ("name", models.CharField(max_length=50)),
                ("price", models.IntegerField()),
                (
                    "description",
                    models.TextField(
                        blank=True, default=None, max_length=200, null=True
                    ),
                ),
                ("icon", models.CharField(blank=True, max_length=2, null=True)),
                ("default_stilletime_product", models.BooleanField(default=False)),
                ("hide_from_api", models.BooleanField(default=False)),
                (
                    "sg_id",
                    models.IntegerField(
                        blank=True, default=None, null=True, unique=True
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="SociSession",
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
                ("name", models.CharField(blank=True, max_length=50, null=True)),
                (
                    "type",
                    models.CharField(
                        choices=[
                            ("SOCIETETEN", "Societeten"),
                            ("STILLETIME", "Stilletime"),
                            ("KRYSSELISTE", "Krysseliste"),
                            ("BURGERLISTE", "Burgerliste"),
                        ],
                        default="SOCIETETEN",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("creation_date", models.DateField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Transfer",
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
                    "created",
                    model_utils.fields.AutoCreatedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="created",
                    ),
                ),
                (
                    "modified",
                    model_utils.fields.AutoLastModifiedField(
                        default=django.utils.timezone.now,
                        editable=False,
                        verbose_name="modified",
                    ),
                ),
                ("amount", models.IntegerField()),
                (
                    "destination",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="destination_transfers",
                        to="economy.socibankaccount",
                    ),
                ),
                (
                    "source",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="source_transfers",
                        to="economy.socibankaccount",
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]
