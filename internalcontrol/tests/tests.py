from django.test import TestCase
from .factories import (
    InternalControlDocumentTemplateFactory,
    InternalControlDocumentItemCollectionTemplateFactory,
    InternalControlDocumentTemplateItemFactory,
)
from internalcontrol.document_generation import (
    create_internal_control_document_from_template,
)


class TestInternalControlDocument(TestCase):
    def setUp(self) -> None:
        self.template_structure_dict = {
            "name": "Edgar søndag",
            "template_item_collections": [
                {
                    "name": "Før åpning",
                    "order": 1,
                    "template_items": [
                        {
                            "content": "Sjekk at det er renolit i beholderen under vasken og vaskemiddel under klitten",
                            "order": 1,
                        },
                        {
                            "content": "Skru på klitten og vask gårsdagens bestikk en siste gang på langt program. "
                            "Skru også på Karen!",
                            "order": 2,
                        },
                        {
                            "content": "Ta bakepapir på Ine, skru henne på og prepp toast",
                            "order": 3,
                        },
                    ],
                },
                {
                    "name": "Under åpningstid",
                    "order": 2,
                    "template_items": [
                        {
                            "content": "Rengjør sigrid nøye, og sjekk at oppskriftsmappen ikke har søl på seg",
                            "order": 1,
                        },
                        {
                            "content": "Puss Mina og seksjonen med Copper Shine Special",
                            "order": 2,
                        },
                        {
                            "content": "Vask hyllene for ølglass over ren og skitten sone",
                            "order": 3,
                        },
                    ],
                },
                {
                    "name": "Etter stengt kjøkken",
                    "order": 3,
                    "template_items": [
                        {
                            "content": "Vask filterbeholderen til Håvard i Klitten",
                            "order": 1,
                        },
                        {
                            "content": "Rensk Oskar, bruk hansker!",
                            "order": 2,
                        },
                        {
                            "content": "Vask all oppvask",
                            "order": 3,
                        },
                    ],
                },
            ],
        }

        self.document_template = InternalControlDocumentTemplateFactory.create(
            name=self.template_structure_dict["name"]
        )

        for collection_template in self.template_structure_dict[
            "template_item_collections"
        ]:
            item_collection_template = (
                InternalControlDocumentItemCollectionTemplateFactory.create(
                    document_template=self.document_template,
                    name=collection_template["name"],
                    order=collection_template["order"],
                )
            )

            for item_template in collection_template["template_items"]:
                InternalControlDocumentTemplateItemFactory.create(
                    item_collection_template=item_collection_template,
                    content=item_template["content"],
                    order=item_template["order"],
                )

    def test__template_generation__generates_documents_properly_v2(self):
        document = create_internal_control_document_from_template(
            self.document_template
        )

        document_collections = document.item_collections.all()
        document_collection_templates = self.template_structure_dict[
            "template_item_collections"
        ]
        self.assertEqual(
            document_collections.count(), len(document_collection_templates)
        )

        for i, document_collection in enumerate(document_collections):
            self.assertEqual(
                document_collection.name, document_collection_templates[i]["name"]
            )

            document_items = document_collection.items.all()
            document_item_templates = document_collection_templates[i]["template_items"]
            self.assertEqual(document_items.count(), len(document_item_templates))

            for j, document_item in enumerate(document_items):
                self.assertEqual(
                    document_item.content, document_item_templates[j]["content"]
                )
