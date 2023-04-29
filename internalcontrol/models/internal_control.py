from django.db import models


class InternalControlDocument(models.Model):
    """
    An internal control document, altså known as IK-liste.
    These are used to actually track the internal control of a given day.
    """

    name = models.CharField(max_length=255)
    template = models.ForeignKey(
        "internalcontrol.InternalControlDocumentTemplate",
        null=True,
        related_name="generated_documents",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return self.name


class InternalControlDocumentItemCollection(models.Model):

    name = models.CharField(max_length=255)
    order = models.IntegerField()
    document = models.ForeignKey(  # Consider renaming to document
        "internalcontrol.InternalControlDocument",
        related_name="item_collections",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.document.name} - {self.name}"


class InternalControlDocumentItem(models.Model):
    """
    An actual item in an internal control document collection.
    Examples:
        - Vask tappekraner
        - Kontroller at alle kraner er stengt
        - Kontroller at alle dører er låst
    """

    class Meta:
        verbose_name = "Internal Control Document Item"
        verbose_name_plural = "Internal Control Document Items"

    content = models.TextField()
    order = models.IntegerField()
    done_by = models.ForeignKey(
        "users.User",
        null=True,
        default=None,
        related_name="internal_control_document_items_done",
        on_delete=models.CASCADE,
    )
    item_collection = models.ForeignKey(  # Consider renaming to item_collection
        "internalcontrol.InternalControlDocumentItemCollection",
        related_name="items",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.item_collection.name} - {self.content}"
