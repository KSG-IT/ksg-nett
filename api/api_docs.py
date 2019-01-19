from drf_yasg.inspectors import SwaggerAutoSchema
from drf_yasg.openapi import Info, Contact
from drf_yasg.views import get_schema_view

SchemaView = get_schema_view(
    info=Info(
        title="KSG X-API",
        default_version='v1',
        contact=Contact(name="Maintained by KSG-IT", email="ksg-it@samfundet.no"),
        x_logo={
            "url": "https://sg.samfundet.no/ekstern/ksg_logo.jpg",
            "backgroundColor": "#FFFFFF",
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
            "* Products can be ordered by creating a `ProductOrder`. "
            "This order is then fulfilled by creating a `Purchase`.\n"
            "* Multiple purchases can be bundled together in a `PurchaseCollection`.\n"
            "* Users can also move money between two SociBankAccounts by creating a `Transfer`.\n\n"
            "The API is fully browsable, so you can start using it by opening the endpoints in your web browser."
        )),
)


class CustomSwaggerAutoSchema(SwaggerAutoSchema):
    def get_tags(self, operation_keys):
        tags = super().get_tags(operation_keys)
        return [tag.capitalize() for tag in tags]

    # Remove clutter since we only use one authentication scheme
    def get_security(self):
        return []
