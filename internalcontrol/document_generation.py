from internalcontrol.models import (
    InternalControlDocument,
    InternalControlDocumentItem,
    InternalControlDocumentItemCollection,
)


def create_internal_control_document_from_template(template):
    document = InternalControlDocument.objects.create(
        name=template.name, template=template
    )
    for collection in template.template_item_collections.all().order_by("order"):
        item_collection = InternalControlDocumentItemCollection.objects.create(
            name=collection.name,
            order=collection.order,
            document=document,
        )
        for item in collection.template_items.all().order_by("order"):
            InternalControlDocumentItem.objects.create(
                content=item.content,
                order=item.order,
                item_collection=item_collection,
            )

    return document
