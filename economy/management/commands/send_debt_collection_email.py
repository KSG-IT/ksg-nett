from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from economy.emails import send_debt_collection_email
from economy.utils import get_indebted_users
from login.util import create_jwt_token_for_user


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

    def send_debt_collection_email(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Sending debt collection emails"
            )
        )

        all_users = options["all_users"]
        users = get_indebted_users(active_users_only=not all_users)

        if not users:
            self.stdout.write(self.style.SUCCESS("No users found. Exiting"))
            return

        list_users = input(f"Found {users.count()} users. List users? [y/n]")

        yes = ["yes", "y"]
        if list_users.lower() in yes:
            for user in users:
                self.stdout.write(
                    f"{user.get_full_name()}: {user.bank_account.balance}\n"
                )

        send_email = input("Send emails? [y/n]")

        if send_email.lower() not in yes:
            self.stdout.write(self.style.SUCCESS("okthxbye"))
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Sending debt collection emails"
            )
        )
        for user in users:
            token = create_jwt_token_for_user(user)
            user_dict = {
                "name": user.get_full_name(),
                "email": user.email,
                "token": token,
                "frontend_url": settings.APP_URL + "/authenticate?token=" + token,
            }
            send_debt_collection_email(user_dict)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Sent email to {user.get_full_name()}"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Done sending debt collection emails. Fingers crossed"
            )
        )
