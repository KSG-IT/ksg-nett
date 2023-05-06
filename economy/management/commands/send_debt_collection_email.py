from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from economy.utils import debt_collection


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.send_debt_collection_email(*args, **options)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-users",
            action="store_true",
            default=False,
            help="Send debt collection emails to all users, not just active users",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Do not send emails, just print to console",
        )

    def send_debt_collection_email(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Sending debt collection emails"
            )
        )

        dry_run = options.get("dry_run", False)
        all_users = options.get("all_users", False)

        user_count = debt_collection(active_users_only=not all_users, dry_run=dry_run)

        output_message = (
            f"{user_count} users found. Dry run. No emails sent"
            if dry_run
            else f"{user_count} emails sent"
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} {output_message}"
            )
        )
