import factory
from internalcontrol.models import (
    InternalControlDocumentTemplate,
    InternalControlDocumentItemCollectionTemplate,
    InternalControlDocumentTemplateItem,
)


class InternalControlDocumentTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InternalControlDocumentTemplate

    name = factory.Faker("name")


class InternalControlDocumentItemCollectionTemplateFactory(
    factory.django.DjangoModelFactory
):
    class Meta:
        model = InternalControlDocumentItemCollectionTemplate

    name = factory.Faker("name")
    order = factory.Faker("pyint")
    internal_control_document_template = factory.SubFactory(
        InternalControlDocumentTemplateFactory
    )


class InternalControlDocumentTemplateItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InternalControlDocumentTemplateItem

    content = factory.Faker("text")
    order = factory.Faker("pyint")
    internal_control_document_item_collection_template = factory.SubFactory(
        InternalControlDocumentItemCollectionTemplateFactory
    )
