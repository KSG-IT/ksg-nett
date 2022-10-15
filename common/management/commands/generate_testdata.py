import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from secrets import token_urlsafe

from users.tests.factories import UserFactory
from economy.models import SociBankAccount, SociProduct, SociSession
from organization.models import InternalGroup, InternalGroupPosition
from admissions.tests.factories import ApplicantFactory, AdmissionFactory
from admissions.consts import AdmissionStatus
from common.util import chose_random_element
from admissions.models import AdmissionAvailableInternalGroupPositionData
from summaries.consts import SummaryType
from summaries.models import Summary
from common.management.commands._consts import (
    SUMMARY_CONTENT,
    QUOTE_CHOICES,
    INTERNAL_GROUP_DATA,
    BANK_ACCOUNT_BALANCE_CHOICES,
)
from common.management.commands._utils import (
    create_semester_dates,
    create_random_economy_activity,
    EconomicActivityType,
    get_random_model_objects,
)
from quotes.models import Quote, QuoteVote
from users.models import User


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

    help = (
        "Generates a variety of models in order to populate "
        "the application with realistic data. Intended to be used with a fresh instance"
    )

    def handle(self, *args, **options):
        try:
            # We start by setting up the base structure
            self.generate_internal_groups_and_positions()
            self.generate_users()

            self.generate_old_admission_data()
            self.generate_summaries()
            self.generate_quotes()
            self.generate_economy()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Something went wrong"))
            raise CommandError(e)
        self.stdout.write(self.style.SUCCESS("Test data generation done"))

    def generate_internal_groups_and_positions(self):
        self.stdout.write(
            self.style.SUCCESS("Generating Internal groups and positions")
        )

        # INTERNAL_GROUP_DATA is a const with a nested dictionary so we can easily defined our base definitions
        for internal_group_data in INTERNAL_GROUP_DATA:
            # Can probably use a transaction.atomic context here
            name = internal_group_data["name"]
            positions = internal_group_data["positions"]
            internal_group_type = internal_group_data["type"]
            internal_group = InternalGroup.objects.create(
                name=name, type=internal_group_type
            )

            self.stdout.write(self.style.SUCCESS(f"Created InternalGroup {name}"))
            for position in positions:
                InternalGroupPosition.objects.create(
                    name=position["name"],
                    internal_group=internal_group,
                    available_externally=position["available_externally"],
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created InternalGroupPosition {position['name']} for InternalGroup {name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS("Finished generating internal groups and positions")
        )

    def generate_users(self, population_size=300):
        self.stdout.write(self.style.SUCCESS("Generating users"))
        users = UserFactory.create_batch(population_size, profile_image=None)

        self.stdout.write(self.style.SUCCESS("Giving users bank accounts"))
        for user in users:
            SociBankAccount.objects.create(card_uuid=None, user=user)
        return users

    def assign_users_to_internal_group_positions(self):
        pass

    def generate_old_admission_data(self):
        """
        Future improvements:
            > Generating history for available internal group positions
            > Generating priorities of each person
        """
        self.stdout.write(self.style.SUCCESS("Generating old admission"))
        # We create 10 admissions dating 5 years back
        now = datetime.date.today()
        january_this_year = datetime.date(year=now.year, month=2, day=12)
        cursor = january_this_year - timezone.timedelta(days=365 * 5)
        semester_offset = timezone.timedelta(days=184)

        generated_admissions = []
        while cursor < january_this_year:
            admission = AdmissionFactory.create(
                date=cursor, status=AdmissionStatus.CLOSED
            )
            applicant_number_choices = [250, 300, 350]
            applicant_size = chose_random_element(applicant_number_choices)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Generating {applicant_size} applicants for {admission.semester}"
                )
            )
            ApplicantFactory.create_batch(applicant_size, admission=admission)

            generated_admissions.append(admission)
            cursor += semester_offset

        self.generate_admission_internal_group_position_data(generated_admissions)
        return generated_admissions

    def generate_admission_internal_group_position_data(self, admissions):
        available_positions_choices = [10, 15, 20, 25]
        for admission in admissions:
            self.stdout.write(
                self.style.SUCCESS(f"Generating available positions for {admission}")
            )
            for position in InternalGroupPosition.get_externally_available_positions():
                available_positions = chose_random_element(available_positions_choices)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Creating {available_positions} spots for {position.name}"
                    )
                )
                AdmissionAvailableInternalGroupPositionData.objects.create(
                    admission=admission,
                    internal_group_position=position,
                    available_positions=available_positions,
                )
        self.stdout.write(self.style.SUCCESS("Done generating available positions"))

    def generate_summaries(self, summary_count=40):
        self.stdout.write(self.style.SUCCESS("Generating summaries"))
        cursor = timezone.make_aware(timezone.datetime.now()) - timezone.timedelta(
            days=365
        )
        day_fraction = 365 / summary_count
        offset = timezone.timedelta(days=day_fraction)

        for _ in range(summary_count):
            for summary_type in SummaryType.choices:
                reporter = get_random_model_objects(User)
                summary = Summary.objects.create(
                    type=summary_type[1],
                    date=cursor,
                    reporter=reporter,
                    contents=SUMMARY_CONTENT,
                )
                participants = get_random_model_objects(User, 13)
                summary.participants.set(participants)
                summary.save()
            cursor += offset

        number_of_summaries = summary_count * len(SummaryType.choices)
        self.stdout.write(
            self.style.SUCCESS(f"{number_of_summaries} summaries generated")
        )

    def generate_quotes(self):
        self.stdout.write(self.style.SUCCESS("Generating Quotes"))
        semesters = create_semester_dates()
        # we create 50 quotes per semester with some offset
        hour_offset = timezone.timedelta(hours=1)
        random_vote_values = range(1, 127)

        for semester in semesters:
            cursor = semester
            for _ in range(50):
                reported_by, verified_by = get_random_model_objects(User, 2)
                random_quote = chose_random_element(QUOTE_CHOICES)
                quote = Quote.objects.create(
                    reported_by=reported_by,
                    verified_by=verified_by,
                    created_at=cursor,
                    text=random_quote["text"],
                    context=random_quote["context"],
                )

                tagged_users_count = chose_random_element([1, 2, 3])
                tagged_users = get_random_model_objects(User, tagged_users_count)
                quote.tagged.set(tagged_users)
                quote.save()

                vote_value = chose_random_element(random_vote_values)
                caster = User.objects.all().order_by("?").first()
                QuoteVote.objects.create(quote=quote, caster=caster, value=vote_value)
                cursor += hour_offset

        number_of_quotes = 50 * len(semesters)
        self.stdout.write(self.style.SUCCESS(f"{number_of_quotes} quotes generated"))

    def generate_economy(self):
        self.stdout.write(self.style.SUCCESS(f"Stimulating economy"))
        # Infuse bank accounts with random balances
        self.stdout.write(
            self.style.SUCCESS(
                f"Injecting all bank accounts with random amount of money"
            )
        )
        for user in User.objects.all():
            user.bank_account.balance = chose_random_element(
                BANK_ACCOUNT_BALANCE_CHOICES
            )
            user.bank_account.save()

        # Create standard soci products
        products = [
            "Tuborg",
            "Dahls",
            "Nordlands",
            "Smirnoff Ice",
            "Pringles",
            "Nudler",
            "Shot",
        ]
        icons = ["🍺", "😡", "🍷", "🛴", "😤", "🙃", "🤢"]
        price_choices = [15, 20, 25, 30, 35, 40, 45, 50, 100]
        self.stdout.write(self.style.SUCCESS(f"Generating soci products"))
        for product in products:
            soci_product = SociProduct.objects.create(
                name=product,
                price=chose_random_element(price_choices),
                sku_number=token_urlsafe(32),
                icon=chose_random_element(icons),
            )
            self.stdout.write(
                self.style.SUCCESS(f"Generated {soci_product.name} {soci_product.icon}")
            )

        # Retrieve a handful of users and pretend they undergo various transactions
        self.stdout.write(
            self.style.SUCCESS(f"Selecting random users to emulate economy")
        )
        users = get_random_model_objects(User, 30)
        economic_activity_choices = [
            EconomicActivityType.TRANSFER,
            EconomicActivityType.DEPOSIT,
            EconomicActivityType.PURCHASE,
        ]

        self.stdout.write(self.style.SUCCESS(f"Creating 3 Soci sessions"))
        soci_session_choices = [SociSession.objects.create() for _ in range(3)]

        for user in users:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Simulating bank account activity for {user.get_full_name()}"
                )
            )
            # Create 30 activity items for each user
            for _ in range(30):
                # Get random action. Either product order, transfer or deposit
                activity = chose_random_element(economic_activity_choices)
                create_random_economy_activity(
                    user,
                    activity,
                    soci_session=chose_random_element(soci_session_choices),
                )

        self.stdout.write(self.style.SUCCESS("Closing opened soci sessions"))
        for session in soci_session_choices:
            session.closed_at = timezone.now()
            session.save()

        self.stdout.write(self.style.SUCCESS("Economy generation done"))

    def generate_schedules(self):
        """
        Should generate what we need to handle setting up shifts
         > Templates
         > Generate future shifts
         > Generate shift interests
         >
        """
        pass
