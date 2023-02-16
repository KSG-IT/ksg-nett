import bleach
from graphene_django_cud.mutations import (
    DjangoCreateMutation,
    DjangoDeleteMutation,
    DjangoPatchMutation,
)

from common.consts import BLEACH_ALLOWED_TAGS
from common.decorators import gql_login_required
from handbook.models import Document
import graphene

from graphene import Node
from graphene_django import DjangoObjectType


class DocumentNode(DjangoObjectType):
    class Meta:
        model = Document
        interfaces = (Node,)

    def resolve_content(self: Document, info):
        return bleach.clean(self.content, tags=BLEACH_ALLOWED_TAGS)

    @classmethod
    @gql_login_required()
    def get_node(cls, info, id):
        return cls._meta.model.objects.get(id=id)


class DocumentQueries(graphene.ObjectType):
    document = Node.Field(DocumentNode)
    all_documents = graphene.List(DocumentNode)

    @gql_login_required()
    def resolve_all_documents(self, info, *args, **kwargs):
        return Document.objects.all().order_by("name")


class CreateDocumentMutation(DjangoCreateMutation):
    class Meta:
        model = Document
        permissions = ("handbook.add_document",)
        auto_context_fields = {
            "created_by": "user",
            "updated_by": "user",
        }


class PatchDocumentMutation(DjangoPatchMutation):
    class Meta:
        model = Document
        permissions = ("handbook.change_document",)
        auto_context_fields = {
            "updated_by": "user",
        }


class DeleteDocumentMutation(DjangoDeleteMutation):
    class Meta:
        model = Document
        permissions = ("handbook.delete_document",)


class HandbookMutations(graphene.ObjectType):
    create_document = CreateDocumentMutation.Field()
    patch_document = PatchDocumentMutation.Field()
    delete_document = DeleteDocumentMutation.Field()
