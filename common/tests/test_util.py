from django.test import TestCase
from common.util import compress_image
from PIL import Image
from django.core.files.base import File
import random
from io import BytesIO
from django.utils import timezone


class TestImageCompression(TestCase):
    def setUp(self):
        self.image = self.get_image_file()
        self.initial_image_size = self.image.size

    @staticmethod
    def get_image_file(
        name="test.jpeg", ext="JPEG", size=(1364, 8000), color=(256, 0, 0)
    ):
        file_obj = BytesIO()
        image = Image.new("RGB", size=size, color=color)
        image.save(file_obj, ext)
        file_obj.seek(0)
        return File(file_obj, name=name)

    def test__image_compression_function__reduces_image_size(self):
        compressed_image = compress_image(self.image, "test", "jpeg")
        self.assertLess(compressed_image.size, self.initial_image_size)


def random_datetime(interval_start, interval_end):
    """Returns a random datetime between two datetime objects"""
    if not interval_start or not interval_end:
        raise ValueError("No arguments can be None")

    delta = interval_end - interval_start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = random.randrange(int_delta)
    return interval_start + timezone.timedelta(seconds=random_second)
