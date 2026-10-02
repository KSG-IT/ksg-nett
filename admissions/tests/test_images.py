import shutil
import tempfile
from io import BytesIO, StringIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from PIL import Image

from admissions.consts import AdmissionStatus
from admissions.schema import PatchApplicantMutation
from admissions.tests.factories import AdmissionFactory, ApplicantFactory
from admissions.utils import (
    copy_applicant_image_to_user,
    delete_applicant_images,
)
from common.util import validate_image_upload
from users.schema import PatchUserMutation
from users.tests.factories import UserFactory


def image_bytes(image_format="JPEG", size=(20, 20)):
    output = BytesIO()
    Image.new("RGB", size, "red").save(output, format=image_format)
    return output.getvalue()


# JPEG encoding is not byte-for-byte stable, so compare against one copy
JPEG = image_bytes()


def upload(name="photo.jpg", content=None):
    return SimpleUploadedFile(name, content or JPEG, "image/jpeg")


class MediaRootTestCase(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.settings_override = override_settings(MEDIA_ROOT=self.media_root)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def applicant_with_image(self, admission=None, name="photo.jpg"):
        applicant = ApplicantFactory(admission=admission or AdmissionFactory())
        applicant.image.save(name, ContentFile(JPEG), save=True)
        return applicant


class TestValidateImageUpload(TestCase):
    def test__jpeg_and_png__returns_format(self):
        self.assertEqual(validate_image_upload(upload()), "JPEG")
        png = upload("photo.png", image_bytes("PNG"))
        self.assertEqual(validate_image_upload(png), "PNG")

    def test__not_an_image__raises(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(upload("photo.jpg", b"<script>"))

    def test__unsupported_format__raises(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(upload("photo.gif", image_bytes("GIF")))

    @override_settings(MAX_IMAGE_UPLOAD_SIZE=100)
    def test__too_large_file__raises(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(upload())

    @override_settings(MAX_IMAGE_PIXELS=100)
    def test__too_many_pixels__raises(self):
        with self.assertRaises(ValidationError):
            validate_image_upload(upload())

    def test__valid_image__can_be_read_after_validation(self):
        image = upload()
        validate_image_upload(image)
        self.assertEqual(image.read(), JPEG)


class TestImageMutationHandlers(TestCase):
    def test__applicant_image__gets_random_name_from_real_format(self):
        image = PatchApplicantMutation.handle_image(
            upload("me.png", image_bytes("JPEG")), "image", None
        )
        self.assertTrue(image.name.endswith(".jpg"))
        self.assertNotIn("me", image.name)

    def test__applicant_image_not_an_image__raises(self):
        with self.assertRaises(ValidationError):
            PatchApplicantMutation.handle_image(
                upload("me.jpg", b"text"), "image", None
            )

    def test__profile_image_not_an_image__raises(self):
        with self.assertRaises(ValidationError):
            PatchUserMutation.handle_profile_image(
                upload("me.jpg", b"text"), "profile_image", None
            )


class TestCopyApplicantImageToUser(MediaRootTestCase):
    def test__copies_image_to_new_file(self):
        applicant = self.applicant_with_image()
        user = UserFactory(profile_image=None)

        copy_applicant_image_to_user(applicant, user)

        user.refresh_from_db()
        self.assertNotEqual(user.profile_image.name, applicant.image.name)
        self.assertTrue(user.profile_image.name.startswith("profiles/"))
        with user.profile_image.open("rb") as copy:
            self.assertEqual(copy.read(), JPEG)

    def test__applicant_without_image__does_nothing(self):
        applicant = ApplicantFactory(admission=AdmissionFactory(), image=None)
        user = UserFactory(profile_image=None)
        copy_applicant_image_to_user(applicant, user)
        user.refresh_from_db()
        self.assertFalse(user.profile_image)


class TestDeleteApplicantImages(MediaRootTestCase):
    def test__deletes_files_and_clears_field(self):
        admission = AdmissionFactory()
        applicant = self.applicant_with_image(admission)
        name = applicant.image.name

        delete_applicant_images(admission)

        applicant.refresh_from_db()
        self.assertFalse(applicant.image)
        self.assertFalse(default_storage.exists(name))

    def test__other_admission__is_not_touched(self):
        applicant = self.applicant_with_image()
        delete_applicant_images(AdmissionFactory())
        self.assertTrue(default_storage.exists(applicant.image.name))

    def test__file_used_as_profile_image__is_kept(self):
        admission = AdmissionFactory()
        applicant = self.applicant_with_image(admission)
        UserFactory(profile_image=applicant.image.name)

        delete_applicant_images(admission)

        self.assertTrue(default_storage.exists(applicant.image.name))


class TestApplicantImageSignals(MediaRootTestCase):
    def test__replaced_image__deletes_old_file(self):
        applicant = self.applicant_with_image()
        old_name = applicant.image.name

        with self.captureOnCommitCallbacks(execute=True):
            applicant.image.save("new.jpg", ContentFile(JPEG), save=True)

        self.assertFalse(default_storage.exists(old_name))
        self.assertTrue(default_storage.exists(applicant.image.name))

    def test__saved_without_image_change__keeps_file(self):
        applicant = self.applicant_with_image()
        with self.captureOnCommitCallbacks(execute=True):
            applicant.first_name = "Ola"
            applicant.save()
        self.assertTrue(default_storage.exists(applicant.image.name))

    def test__deleted_applicant__deletes_file(self):
        applicant = self.applicant_with_image()
        name = applicant.image.name
        with self.captureOnCommitCallbacks(execute=True):
            applicant.delete()
        self.assertFalse(default_storage.exists(name))


class TestDeleteClosedAdmissionImagesCommand(MediaRootTestCase):
    def setUp(self):
        super().setUp()
        self.closed = self.applicant_with_image(
            AdmissionFactory(status=AdmissionStatus.CLOSED), "closed.jpg"
        )
        self.shared = self.applicant_with_image(
            AdmissionFactory(status=AdmissionStatus.CLOSED), "shared.jpg"
        )
        UserFactory(profile_image=self.shared.image.name)
        self.active = self.applicant_with_image(
            AdmissionFactory(status=AdmissionStatus.OPEN), "active.jpg"
        )
        self.orphan = default_storage.save(
            "applicants/orphan.jpg", ContentFile(JPEG)
        )

    def run_command(self, *args):
        call_command("delete_closed_admission_images", *args, stdout=StringIO())

    def test__dry_run__deletes_nothing(self):
        self.run_command("--dry-run")
        for name in [self.closed.image.name, self.active.image.name, self.orphan]:
            self.assertTrue(default_storage.exists(name))

    def test__deletes_closed_and_unused_images(self):
        self.run_command()
        self.assertFalse(default_storage.exists(self.closed.image.name))
        self.assertFalse(default_storage.exists(self.orphan))
        self.assertTrue(default_storage.exists(self.shared.image.name))
        self.assertTrue(default_storage.exists(self.active.image.name))

