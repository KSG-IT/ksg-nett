from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from economy.models import SociSession


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.close_stale_session()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def close_stale_session(self):
        """
        Run this using a crontab. Runs script close_stale.sh
        """
        session = SociSession.get_active_session()
        if not session:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} No active session found"
                )
            )
            return

        last_purchase = session.product_orders.order_by("-purchased_at").first()
        if not last_purchase:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} No purchases found"
                )
            )
            return
        purchase_delta = timezone.now() - last_purchase.purchased_at
        hours = purchase_delta.total_seconds() / 3600
        if hours >= 2:
            self.stdout.write(
                self.style.SUCCESS(
                    f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Session last purchase is more than 2 hours ago, closing session"
                )
            )
            session.closed_at = timezone.now()
            session.save()
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"{timezone.now().strftime('%Y-%d-%m, %H:%M:%S')} Session last purchase is less than 2 hours ago, not closing session"
            )
        )
