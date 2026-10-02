from django.db import transaction
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

from admissions.models import Applicant
from common.util import delete_unused_media_file


@receiver(pre_save, sender=Applicant)
def delete_replaced_applicant_image(sender, instance: Applicant, **kwargs):
    if not instance.pk:
        return
    old_name = (
        Applicant.objects.filter(pk=instance.pk).values_list("image", flat=True).first()
    )
    if old_name and old_name != instance.image.name:
        transaction.on_commit(lambda: delete_unused_media_file(old_name))


@receiver(post_delete, sender=Applicant)
def delete_applicant_image(sender, instance: Applicant, **kwargs):
    name = instance.image.name
    if name:
        transaction.on_commit(lambda: delete_unused_media_file(name))
