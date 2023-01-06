from drf_yasg2.inspectors import SwaggerAutoSchema
from drf_yasg2.openapi import Info, Contact
from drf_yasg2.views import get_schema_view
from rest_framework.permissions import AllowAny

from ksg_nett import settings

SchemaView = get_schema_view(
    permission_classes=(AllowAny,),
    public=True,
    info=Info(
        title="KSG X-API",
        default_version="v1",
        contact=Contact(name="Maintained by KSG-IT", email="ksg-it@samfundet.no"),
        x_logo={
            "url": "https://sg.samfundet.no/ekstern/ksg_logo.jpg",
        },
        description=(
            "---\n"
            "### This is the API reference for the web services of Kafé- og Serveringsgjengen (KSG) "
            "at Studentersamfundet i Trondhjem.\n"
            "The API's main focus is to handle economy features at Societeten (Soci), KSG's own \"hybel\".\n\n"
            "Here are some important definitions: \n"
            "* Each user has their own `SociBankAccount`, which keeps track of that user's balance.\n"
            "* Users deposit money into their SociBankAccount by creating a `Deposit`.\n"
            "* A `SociProduct` is a product for sale at Soci.\n"
            "* Whenever someone ''opens'' Soci, a `SociSession` is created, which tracks the time period in which Soci "
            "was open.\n"
            "* Products can be ordered by creating a `ProductOrder`. "
            "One or multiple orders are then fulfilled by creating a `Purchase`. "
            "All purchases made are automatically linked to the active SociSession. \n"
            "* Users can also move money between two SociBankAccounts by creating a `Transfer`.\n\n"
            "The API is fully browsable, so you can start using it by opening the endpoints in your web browser."
        ),
    ),
)

settings.SWAGGER_SETTINGS["SECURITY_DEFINITIONS"] = {
    "Basic": {
        "type": "basic",
        "description": "Standard username/password based authentication. Only available for staff users.",
    },
    "JWT": {
        "type": "apiKey",
        "name": "Authorization",
        "in": "header",
        "description": "The preferred authentication scheme for the KSG API is JSON Web Tokens (JWT). \n\n"
        "### Obtaining a token\n\n"
        "Do a **POST** request to [/api/authentication/obtain-token](#section/Authentication/JWT) "
        "with the following payload:\n\n"
        '    {"username": `CARD_UUID`}\n\n'
        f"**Note:** Each obtained token expires after {settings.SIMPLE_JWT['SLIDING_TOKEN_LIFETIME'].days * 24} "
        "hours.\n\n"
        "---\n\n"
        "### Authenticate with a token\n\n"
        "Send the token in the HTTP_AUTHORIZATION header, prefixed with "
        f"`{settings.SIMPLE_JWT['AUTH_HEADER_TYPES'][0]}` (+ space):\n\n"
        f"    Authorization: {settings.SIMPLE_JWT['AUTH_HEADER_TYPES'][0]} "
        "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lk...\n\n"
        "---\n\n"
        "### Verifying a token\n\n"
        "Do a **POST** request to [/api/authentication/verify-token](#section/Authentication/JWT) "
        "with the following payload:\n\n"
        '    {"token": `TOKEN`}\n\n'
        "If the token is still valid, a HTTP `200` status will be returned.\n\n"
        "---\n\n"
        "### Refreshing a token\n\n"
        "Do a **POST** request to [/api/authentication/refresh-token](#section/Authentication/JWT) "
        "with the following payload:\n\n"
        '    {"token": `TOKEN`}\n\n'
        "**Note:** You cannot refresh an expired token.\n\n"
        "---\n\n"
        "### Invalidating a token\n\n"
        "There's currently no way to manually invalidate a token. You should instead delete the token from "
        "the client application, and then the token will be automatically invalidated after the expiration "
        "date passes.",
    },
}


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys):
        tags = super().get_tags(operation_keys)
        return [tag.capitalize() for tag in tags]

    # Remove authentication boilerplate text from views
    def get_security(self):
        return []
