# Generated by Django 3.2.18 on 2023-04-29 13:25

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("internalcontrol", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="internalcontroldocumentitem",
            old_name="internal_control_document_item_collection",
            new_name="item_collection",
        ),
        migrations.RenameField(
            model_name="internalcontroldocumentitemcollection",
            old_name="internal_control_document",
            new_name="document",
        ),
        migrations.RenameField(
            model_name="internalcontroldocumentitemcollectiontemplate",
            old_name="internal_control_document_template",
            new_name="document_template",
        ),
        migrations.RenameField(
            model_name="internalcontroldocumenttemplateitem",
            old_name="internal_control_document_item_collection_template",
            new_name="item_collection_template",
        ),
    ]
