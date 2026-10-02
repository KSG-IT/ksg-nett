from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand

from admissions.consts import AdmissionStatus
from admissions.models import Admission, Applicant
from admissions.utils import delete_applicant_images
from users.models import User

APPLICANT_IMAGE_DIR = "applicants"


class Command(BaseCommand):
    help = (
        "Deletes the images of applicants in closed admissions, and files in "
        f"media/{APPLICANT_IMAGE_DIR}/ that no applicant uses. Files that a "
        "user uses as profile image are kept."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Only print what would be deleted",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        closed_admissions = Admission.objects.filter(status=AdmissionStatus.CLOSED)
        closed_images = (
            Applicant.objects.filter(admission__in=closed_admissions)
            .exclude(image__isnull=True)
            .exclude(image="")
        )
        self.stdout.write(
            f"Applicant images in closed admissions: {closed_images.count()}"
        )
        if not dry_run:
            for admission in closed_admissions:
                delete_applicant_images(admission)

        used = set(
            Applicant.objects.exclude(image__isnull=True)
            .exclude(image="")
            .values_list("image", flat=True)
        ) | set(
            User.objects.exclude(profile_image="").values_list(
                "profile_image", flat=True
            )
        )
        if not default_storage.exists(APPLICANT_IMAGE_DIR):
            return
        _, files = default_storage.listdir(APPLICANT_IMAGE_DIR)
        unused = [
            f"{APPLICANT_IMAGE_DIR}/{name}"
            for name in files
            if f"{APPLICANT_IMAGE_DIR}/{name}" not in used
        ]
        self.stdout.write(f"Unused files in {APPLICANT_IMAGE_DIR}/: {len(unused)}")
        if not dry_run:
            for name in unused:
                default_storage.delete(name)
        self.stdout.write(
            self.style.SUCCESS("Dry run, nothing deleted" if dry_run else "Done")
        )
