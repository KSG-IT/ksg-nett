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
        template = (
            self.internal_control_document_template
        ) = InternalControlDocumentTemplateFactory.create(name="Edgar søndag")
        before_opening = (
            self.internal_control_document_item_collection_template
        ) = InternalControlDocumentItemCollectionTemplateFactory.create(
            internal_control_document_template=self.internal_control_document_template,
            name="Før åpning",
        )
        under_opening = (
            self.internal_control_document_item_collection_template
        ) = InternalControlDocumentItemCollectionTemplateFactory.create(
            internal_control_document_template=self.internal_control_document_template,
            name="Under åpningstid",
        )
        closing = (
            self.internal_control_document_item_collection_template
        ) = InternalControlDocumentItemCollectionTemplateFactory.create(
            internal_control_document_template=self.internal_control_document_template,
            name="Etter stengt kjøkken",
        )

        # Before opening
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=before_opening,
            content="Sjekk at det er renolit i beholderen under vasken og vaskemiddel under klitten",
        )
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=before_opening,
            content="Skru på klitten og vask gårsdagens bestikk en siste gang på langt program. Skru også på Karen!",
        )
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=before_opening,
            content="Ta bakepapir på Ine, skru henne på og prepp toast",
        )

        # Under opening
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=under_opening,
            content="Rengjør sigrid nøye, og sjekk at oppskriftsmappen ikke har søl på seg",
        )
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=under_opening,
            content="Puss Mina og seksjonen med Copper Shine Special",
        )
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=under_opening,
            content="Vask hyllene for ølglass over ren og skitten sone",
        )

        # During closing
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=closing,
            content="Vask filterbeholderen til Håvard i Klitten",
        )
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=closing,
            content="Rensk Oskar, bruk hansker!",
        )
        InternalControlDocumentTemplateItemFactory.create(
            internal_control_document_item_collection_template=closing,
            content="Vask all oppvask",
        )

    def test__internal_control_document_template__model_relationship_structure(self):
        pretty_print_internal_control_document_template(
            self.internal_control_document_template
        )

    def test__template_generation__generates_documents_properly(self):

        document = create_internal_control_document_from_template(
            self.internal_control_document_template
        )
        pretty_print_internal_control_document_template(
            self.internal_control_document_template
        )
        pretty_print_internal_control_document(document)
