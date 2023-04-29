from django.test import TestCase
from .factories import (
    InternalControlDocumentTemplateFactory,
    InternalControlDocumentItemCollectionTemplateFactory,
    InternalControlDocumentTemplateItemFactory,
)
from internalcontrol.string_utils import (
    pretty_print_internal_control_document_template,
    pretty_print_internal_control_document,
)
from internalcontrol.document_generation import (
    create_internal_control_document_from_template,
)


class TestInternalControlDocument(TestCase):
    def setUp(self) -> None:

        self.document_template = InternalControlDocumentTemplateFactory.create(
            name="Edgar søndag"
        )
        before_opening = (
            self.internal_control_document_item_collection_template
        ) = InternalControlDocumentItemCollectionTemplateFactory.create(
            document_template=self.document_template,
            name="Før åpning",
            order=1,
        )
        under_opening = (
            self.internal_control_document_item_collection_template
        ) = InternalControlDocumentItemCollectionTemplateFactory.create(
            document_template=self.document_template,
            name="Under åpningstid",
            order=2,
        )
        closing = (
            self.internal_control_document_item_collection_template
        ) = InternalControlDocumentItemCollectionTemplateFactory.create(
            document_template=self.document_template,
            name="Etter stengt kjøkken",
            order=3,
        )

        # Before opening
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=before_opening,
            content="Sjekk at det er renolit i beholderen under vasken og vaskemiddel under klitten",
            order=1,
        )
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=before_opening,
            content="Skru på klitten og vask gårsdagens bestikk en siste gang på langt program. Skru også på Karen!",
            order=2,
        )
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=before_opening,
            content="Ta bakepapir på Ine, skru henne på og prepp toast",
            order=3,
        )

        # Under opening
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=under_opening,
            content="Rengjør sigrid nøye, og sjekk at oppskriftsmappen ikke har søl på seg",
            order=1,
        )
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=under_opening,
            content="Puss Mina og seksjonen med Copper Shine Special",
            order=2,
        )
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=under_opening,
            content="Vask hyllene for ølglass over ren og skitten sone",
            order=3,
        )

        # During closing
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=closing,
            content="Vask filterbeholderen til Håvard i Klitten",
            order=1,
        )
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=closing,
            content="Rensk Oskar, bruk hansker!",
            order=2,
        )
        InternalControlDocumentTemplateItemFactory.create(
            item_collection_template=closing, content="Vask all oppvask", order=3
        )

    def test__template_generation__generates_documents_properly(self):
        document = create_internal_control_document_from_template(
            self.document_template
        )

        document_collections = document.item_collections.all()
        document_collection_templates = (
            self.document_template.template_item_collections.all()
        )
        self.assertEqual(document_collections.count(), 3)
        self.assertEqual(
            document_collections[0].name, document_collection_templates[0].name
        )
        self.assertEqual(
            document_collections[1].name, document_collection_templates[1].name
        )
        self.assertEqual(
            document_collections[2].name, document_collection_templates[2].name
        )

        document_items = document_collections[0].items.all()
        document_item_templates = document_collection_templates[0].template_items.all()
        self.assertEqual(document_items.count(), 3)
        self.assertEqual(document_items[0].content, document_item_templates[0].content)
        self.assertEqual(document_items[1].content, document_item_templates[1].content)
        self.assertEqual(document_items[2].content, document_item_templates[2].content)

        document_items = document_collections[1].items.all()
        document_item_templates = document_collection_templates[1].template_items.all()
        self.assertEqual(document_items.count(), 3)
        self.assertEqual(document_items[0].content, document_item_templates[0].content)
        self.assertEqual(document_items[1].content, document_item_templates[1].content)
        self.assertEqual(document_items[2].content, document_item_templates[2].content)

        document_items = document_collections[2].items.all()
        document_item_templates = document_collection_templates[2].template_items.all()
        self.assertEqual(document_items.count(), 3)
        self.assertEqual(document_items[0].content, document_item_templates[0].content)
        self.assertEqual(document_items[1].content, document_item_templates[1].content)
        self.assertEqual(document_items[2].content, document_item_templates[2].content)
