import sentry_sdk
from django.core.exceptions import PermissionDenied
from graphene_file_upload.django import FileUploadGraphQLView
from graphql import GraphQLError

from api.exceptions import InsufficientFundsException
from common.exceptions import IllegalOperation

# Errors that resolvers raise on purpose to tell the client "no". A purchase
# without enough money on the account is one (placeProductOrder).
EXPECTED_ERRORS = (
    PermissionDenied,
    IllegalOperation,
    GraphQLError,
    InsufficientFundsException,
)


class SentryGraphQLView(FileUploadGraphQLView):
    """
    graphene-django calls graphql-core directly, so Sentry's GrapheneIntegration
    never runs. Without this view every transaction is named "/graphql/", and
    resolver exceptions end up only in the response "errors" list.
    """

    def execute_graphql_request(
        self, request, data, query, variables, operation_name, show_graphiql=False
    ):
        sentry_sdk.get_current_scope().set_transaction_name(
            operation_name or "anonymous GraphQL operation", source="custom"
        )
        result = super().execute_graphql_request(
            request, data, query, variables, operation_name, show_graphiql
        )
        for error in (result.errors if result else None) or []:
            original = getattr(error, "original_error", None)
            if original is not None and not isinstance(original, EXPECTED_ERRORS):
                sentry_sdk.capture_exception(original)
        return result
