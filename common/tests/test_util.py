from django.test import TestCase
from common.util import compress_image
from PIL import Image
from django.core.files.base import File
from io import BytesIO


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
        compressed_image = compress_image(
            self.image, max_width=6000, max_height=2000, quality=70
        )
        self.assertLess(compressed_image.size, self.initial_image_size)
