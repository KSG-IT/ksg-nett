from django.db import models


class InternalControlDocumentTemplate(models.Model):
    """
    A template for an internal control document, altså known as IK-liste.
    These are the equivalent to the 'unfulled' lists in analog times. These
    are used to generate the actual lists that are used to track the internal
    control of a given day.
    """

    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class InternalControlDocumentItemCollectionTemplate(models.Model):
    """
    Template for a colleciton of items in an internal control document.
    Used to group together items that are related to each other. For example,
    - IK-rutiner før åpning
    - IK-rutiner under åpning
    - IK-rutiner under stenging
    """

    name = models.CharField(max_length=255)
    order = models.IntegerField()
    internal_control_document_template = models.ForeignKey(
        "internalcontrol.InternalControlDocumentTemplate",
        related_name="template_item_collections",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.internal_control_document_template.name} - {self.name}"


class InternalControlDocumentTemplateItem(models.Model):
    """
    Template for an actual item in an internal control document collection.
    Examples:
        - Vask tappekraner
        - Kontroller at alle kraner er stengt
        - Kontroller at alle dører er låst
    """

    class Meta:
        verbose_name = "Internal Control Document Template Item"
        verbose_name_plural = "Internal Control Document Template Items"

    content = models.TextField()
    order = models.IntegerField()
    internal_control_document_item_collection_template = models.ForeignKey(
        "internalcontrol.InternalControlDocumentItemCollectionTemplate",
        related_name="template_items",
        on_delete=models.CASCADE,
    )

    def __str__(self):
        return f"{self.internal_control_document_item_collection_template.name} - {self.content}"
