from django.test import TestCase
import datetime

from common.util import (
    compress_image,
    date_time_combiner,
    midnight_timestamps_from_date,
)
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


class TestBleachAllowedTags(TestCase):
    def test__rich_text_editor_marks__are_not_escaped(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        # Marks the frontend editor (tiptap StarterKit) can produce
        html = "<p><strong>b</strong> <em>i</em> <u>u</u> <s>s</s></p>"
        self.assertEqual(bleach.clean(html, tags=BLEACH_ALLOWED_TAGS), html)

    def test__attributes_on_underline__are_stripped(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        self.assertEqual(
            bleach.clean('<u onclick="x()">u</u>', tags=BLEACH_ALLOWED_TAGS),
            "<u>u</u>",
        )

    def test__every_allowed_tag__is_kept(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        for tag in sorted(BLEACH_ALLOWED_TAGS):
            with self.subTest(tag=tag):
                html = f"<{tag}>" if tag in ("br", "hr") else f"<{tag}>x</{tag}>"
                # The HTML parser drops a <th> outside a <table>, and <table>
                # is not allowed.
                expected = "x" if tag == "th" else html
                self.assertEqual(bleach.clean(html, tags=BLEACH_ALLOWED_TAGS), expected)

    def test__disallowed_tags__are_escaped(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        for html in [
            "<script>alert(1)</script>",
            '<img src="x" onerror="alert(1)">',
            '<iframe src="https://example.com"></iframe>',
        ]:
            with self.subTest(html=html):
                cleaned = bleach.clean(html, tags=BLEACH_ALLOWED_TAGS)
                self.assertNotIn("<", cleaned)
                self.assertIn("&lt;", cleaned)

    def test__safe_link__is_kept(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        html = '<a href="https://ksg-nett.no" title="KSG">KSG</a>'
        self.assertEqual(bleach.clean(html, tags=BLEACH_ALLOWED_TAGS), html)

    def test__javascript_link__loses_href(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        self.assertEqual(
            bleach.clean(
                '<a href="javascript:alert(1)">x</a>', tags=BLEACH_ALLOWED_TAGS
            ),
            "<a>x</a>",
        )

    def test__style_and_event_attributes__are_stripped(self):
        import bleach
        from common.consts import BLEACH_ALLOWED_TAGS

        self.assertEqual(
            bleach.clean(
                '<span style="color: red" onmouseover="x()">s</span>',
                tags=BLEACH_ALLOWED_TAGS,
            ),
            "<span>s</span>",
        )


class TestLocalTimeHelpers(TestCase):
    def test__date_time_combiner__uses_local_offset(self):
        winter = date_time_combiner(datetime.date(2026, 1, 15), datetime.time(12, 0))
        summer = date_time_combiner(datetime.date(2026, 7, 15), datetime.time(12, 0))
        self.assertEqual(winter.utcoffset(), datetime.timedelta(hours=1))
        self.assertEqual(summer.utcoffset(), datetime.timedelta(hours=2))
        self.assertEqual((winter.hour, winter.minute), (12, 0))

    def test__midnight_timestamps_from_date__spans_the_local_day(self):
        early, late = midnight_timestamps_from_date(datetime.date(2026, 7, 15))
        self.assertEqual(early.utcoffset(), datetime.timedelta(hours=2))
        self.assertEqual((early.hour, early.minute), (0, 0))
        self.assertEqual((late.hour, late.minute, late.second), (23, 59, 59))
