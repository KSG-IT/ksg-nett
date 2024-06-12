def pretty_print_internal_control_document_template(internal_control_document_template):
    """
    Pretty prints an internal control document template. For debug purposes.
    """
    print(internal_control_document_template.name)
    for (
        item_collection
    ) in internal_control_document_template.template_item_collections.all().order_by(
        "order"
    ):
        print(f"  {item_collection.name}")
        for item in item_collection.template_items.all().order_by("order"):
            print(f"    {item.content}")


def pretty_print_internal_control_document(internal_control_document):
    """
    Pretty prints an internal control document. For debug purposes.
    """
    print(internal_control_document.name)
    for item_collection in internal_control_document.item_collections.all().order_by(
        "order"
    ):
        print(f"  {item_collection.name}")
        for item in item_collection.items.all().order_by("order"):
            content_string = item.content
            if item.done_by:
                content_string = "    (done) " + content_string
            else:
                content_string = "(not done) " + content_string
            print(f"    {content_string}")
