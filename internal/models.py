from django.db import models
from common.util import compress_image


class Commission(models.Model):
    pass


class SlideshowImage(models.Model):
    class Meta:
        verbose_name = "Slideshow image"
        verbose_name_plural = "Slideshow images"

    image = models.ImageField(upload_to='slideshow/')
    description = models.CharField(max_length=200)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

    def save(self, *args, **kwargs):
        img = self.image
        self.image = compress_image(img, 900, 600, 80)
        super(SlideshowImage, self).save(*args, **kwargs)
