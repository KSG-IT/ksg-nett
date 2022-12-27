import enum

from django.db import models


class DocumentTypeEnum(enum.Enum):
    FILE = "FILE"
    DOCUMENT = "DOCUMENT"


class Document(models.Model):
    """
    A document is either markdown content or a file. We do this so we can
    store both types in the same table.
    """

    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    name = models.CharField(max_length=100)

    # Content or File can exist but not both
    content = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="created_documents",
    )
    updated_by = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="updated_documents",
    )

    def __str__(self):
        return self.name
