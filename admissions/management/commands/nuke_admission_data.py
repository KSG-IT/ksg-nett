from django.core.management.base import BaseCommand, CommandError
from admissions.models import Admission, Interview, Applicant, InterviewLocation


class Command(BaseCommand):
    """
    This is a fairly large model generation script. One of the main caveats with the main implementation now
    is that is in no way modular and can only be run once due to factory.sequence usage which will
    cause unique constraint errors when using without nuking several database tables.

    Future improvements:
        > Move generation into helpers that reside at at app-level instead of them all being here
        > Wrap script in exception blocks so that it can be used a bit more easily
        > Allow for modular usage (Lets say you just want users and not quotes or the other way around. Would
        be nice if we could target specific modules of the application for data generation)
    """

    help = "Nukes admission data"

    def handle(self, *args, **options):
        try:
            # We start by setting up the base structure
            self.stdout.write(self.style.SUCCESS("🧨 Admission model "))
            Admission.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("🧨 InterviewLocation model"))
            InterviewLocation.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("🧨 Interview model"))
            Interview.objects.all().delete()
            self.stdout.write(self.style.SUCCESS("🧨 Applicant model"))
            Applicant.objects.all().delete()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Something went wrong"))
            raise CommandError(e)
        self.stdout.write(self.style.SUCCESS("Nuking complete"))
