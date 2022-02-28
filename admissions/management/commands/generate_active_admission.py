from django.core.management.base import BaseCommand, CommandError
from admissions.models import Admission, Applicant


class Command(BaseCommand):
    """
    Algorithm:
        1. Generate default interview schedule template if it does not exist
            - Should create an interview period which started a week ago and has another week left
        2. Generate interviews
        3. Generate available positions
        4. Randomize applicants
            - Their state in the interview process
            - Their priorities
        5. Randomize interviews
            - Content
            - Interviewers
    """

    def handle(self, *args, **options):
        try:
            pass

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Something went wrong"))
            raise CommandError(e)
        self.stdout.write(self.style.SUCCESS("Active admission has been generated"))

    def generate_interview_schedule(self):
        pass

    def generate_available_positions(self):
        pass

    def generate_interviews(self):
        pass

    def generate_applicants(self):
        pass

    def randomize_interviews(self):
        pass
