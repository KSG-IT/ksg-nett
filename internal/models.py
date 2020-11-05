from django.db import models


class Commission(models.Model):
    pass



class Slideshow(models.Model):
    image = models.ImageField(upload_to = 'slideshow/')
    description = models.CharField(max_length = 200)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()

