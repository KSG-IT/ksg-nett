from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from legacy.models import Varer, Kryss, Innkryssinger
from economy.models import SociProduct, SociSession, ProductOrder, SociBankAccount
from users.models import User


def create_session_and_orders_from_legacy_session(
    legacy_session: Innkryssinger, type: SociSession.Type
):
    created_by = legacy_session.innkrysser
    name = ""
    if type == SociSession.Type.KRYSELLISTE:
        name = legacy_session.kommentar[:50]

    if created_by:
        created_by = User.objects.get(sg_id=created_by.id)
    else:
        created_by = None

    new_session = SociSession(
        type=type,
        name=name,
        created_by=created_by,
        creation_date=legacy_session.kryssetid,
    )
    purchases = Kryss.objects.using("legacy").filter(innkryssing=legacy_session)
    purchase_list = []
    for purchase in purchases:
        product_order = {
            "session": new_session,
            "product": SociProduct.objects.get(sg_id=purchase.vare.id),
            "order_size": purchase.antall,
            "cost": purchase.vare.pris * purchase.antall,
            "source": SociBankAccount.objects.get(user__sg_id=purchase.person.id),
            "purchased_at": purchase.kryssetid,
        }
        purchase_list.append(product_order)

    if purchase_list:
        new_session.save()
        new_session.refresh_from_db()
        # Override auto_fields
        new_session.created_at = legacy_session.kryssetid
        new_session.updated_at = legacy_session.registrert
        new_session.closed_at = legacy_session.registrert
        new_session.save()

        for purchase in purchase_list:
            purchase_obj = ProductOrder.objects.create(**purchase)
            if purchase["purchased_at"]:
                purchase_obj.purchased_at = purchase["purchased_at"]
            else:
                purchase_obj.purchased_at = new_session.closed_at
            purchase_obj.save()

    print(f"Created session of {len(purchase_list)} orders")


class Command(BaseCommand):
    def handle(self, *args, **options):
        try:
            self.migrate_sessions()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"{e}"))
            raise CommandError(e)

    def migrate_sessions(self):
        self.stdout.write(self.style.SUCCESS("Migrating legacy products to new table"))
        legacy_products = Varer.objects.using("legacy").all()
        for product in legacy_products:
            with transaction.atomic():
                try:
                    self.stdout.write(
                        self.style.SUCCESS(f"Migrating product: {product.navn}")
                    )
                    SociProduct.objects.create(
                        sku_number=product.navn,
                        name=product.navn,
                        price=product.pris,
                        description=product.beskrivelse,
                        default_stilletime_product=False,
                        hide_from_api=True,
                        sg_id=product.id,
                    )
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"{e}"))
        legacy_purchases = Kryss.objects.using("legacy").all()
        legacy_soci_sessions = Innkryssinger.objects.using("legacy").all()

        self.stdout.write(self.style.SUCCESS("Migrating legacy purchases to new table"))
        self.stdout.write(
            self.style.SUCCESS(f"Migrating {len(legacy_purchases)} purchases")
        )

        self.stdout.write(
            self.style.SUCCESS("Migrating legacy soci sessions to new table")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Migrating {len(legacy_soci_sessions)} soci sessions")
        )

        stille = legacy_soci_sessions.filter(kommentar__icontains="Stille")
        digi = legacy_soci_sessions.filter(kommentar__icontains="digi")
        rest = legacy_soci_sessions.exclude(kommentar__icontains="stille").exclude(
            kommentar__icontains="digi"
        )
        with transaction.atomic():
            for session in stille:
                self.stdout.write(
                    self.style.SUCCESS(f"Creating session {session.kommentar}")
                )

                create_session_and_orders_from_legacy_session(
                    session, type=SociSession.Type.STILLETIME
                )
            for session in digi:
                self.stdout.write(
                    self.style.SUCCESS(f"Creating session {session.kommentar}")
                )

                create_session_and_orders_from_legacy_session(
                    session, type=SociSession.Type.SOCIETETEN
                )
            for session in rest:
                self.stdout.write(
                    self.style.SUCCESS(f"Creating session {session.kommentar}")
                )
                create_session_and_orders_from_legacy_session(
                    session, type=SociSession.Type.KRYSELLISTE
                )

        self.stdout.write(self.style.SUCCESS(f"stille: {stille.count()}"))
        self.stdout.write(self.style.SUCCESS(f"rest: {rest.count()}"))
