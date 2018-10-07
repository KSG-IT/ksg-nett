from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from api.serializers import ChargeSociBankAccountDeserializer
from api.views import CheckBalanceView, ChargeSociBankAccountView

# This file is used for creating decorated views to be used in the API docs resource

decorated_balance_view = swagger_auto_schema(
    method='get',
    manual_parameters=[openapi.Parameter(
        name='card-number', in_=openapi.IN_HEADER,
        description="The RFID card id connected to a user's Soci bank account",
        type=openapi.TYPE_INTEGER, required=True
    )],
    responses={
        402: ": This Soci account cannot be charged due to insufficient funds",
        404: ": Could not retrieve Soci account from the provided card number",
    },
)(CheckBalanceView.as_view())

decorated_charge_view = swagger_auto_schema(
    request_body=ChargeSociBankAccountDeserializer,
    method='post',
    manual_parameters=[openapi.Parameter(
        name='card-number', in_=openapi.IN_HEADER,
        description="The RFID card id connected to a user's Soci bank account",
        type=openapi.TYPE_INTEGER, required=True
    )],
    responses={
        400: ": Illegal input",
        402: ": This Soci account cannot be charged due to insufficient funds",
        404: ": Could not retrieve Soci account from the provided card number",
    },
)(ChargeSociBankAccountView.as_view())
