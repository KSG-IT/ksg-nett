from django.db import models


class Document(models.Model):
    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"

    name = models.CharField(max_length=100)
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
