import pytz
import factory
import factory.fuzzy
from django.utils import timezone
from admissions.models import (
    Applicant,
    InterviewLocation,
    InterviewLocationAvailability,
    Admission,
)


class AdmissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Admission


class ApplicantFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Applicant

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Sequence(lambda n: f"someapplicant{n}@applicant.com")
    phone = factory.Sequence(lambda n: f"450877{n}")
    hometown = factory.Faker("address")
    address = factory.Faker("address")
    date_of_birth = factory.Faker("date")


class InterviewLocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewLocation

    name = factory.fuzzy.FuzzyChoice(
        ["Knaus", "Bodegaen", "Biblioteket", "Digitalt rom 1", "Digitalt rom 2"]
    )


class InterviewLocationAvailabilityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterviewLocationAvailability

    location = factory.SubFactory(InterviewLocationFactory)

    datetime_from = factory.LazyFunction(timezone.now)
    datetime_to = factory.LazyFunction(
        lambda x: timezone.now() + timezone.timedelta(hours=8)
    )
