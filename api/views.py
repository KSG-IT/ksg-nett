from drf_yasg.openapi import Parameter, IN_HEADER, TYPE_INTEGER
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from api.serializers import CheckBalanceSerializer, SociProductSerializer, ChargeSociBankAccountDeserializer, \
    PurchaseSerializer
from api.view_mixins import CustomCreateAPIView
from economy.models import SociBankAccount, SociProduct, Purchase


class SociProductListView(ListAPIView):
    """
    Retrieves a list of products that can be purchased at Soci.
    """
    serializer_class = SociProductSerializer
    queryset = SociProduct.objects.all()

    @swagger_auto_schema(operation_summary="List SociProducts")
    def get(self, request, *args, **kwargs):
        soci_products = self.get_queryset()
        serializer = self.get_serializer(soci_products, many=True)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)


class SociBankAccountBalanceDetailView(RetrieveAPIView):
    """
    Checks the available balance of an account, based on the provided RFID card number.
    """
    serializer_class = CheckBalanceSerializer

    @swagger_auto_schema(
        operation_summary="Retrieve SociBankAccount balance",
        manual_parameters=[Parameter(
            name='card-number',
            in_=IN_HEADER,
            description="The RFID card id connected to a user's Soci bank account",
            type=TYPE_INTEGER,
            required=True
        )],
        responses={
            "402": ": This SociBankAccount cannot be charged due to insufficient funds",
            "404": ": Could not retrieve SociBankAccount from the provided card number",
        },
    )
    def get(self, request, *args, **kwargs):
        card_uuid = self.request.META.get('HTTP_CARD_NUMBER', None)
        soci_bank_account: SociBankAccount = self._get_account_from_card_id(card_uuid=card_uuid)
        serializer = self.get_serializer(soci_bank_account)
        data = serializer.data

        response_status = status.HTTP_200_OK
        if not soci_bank_account.has_sufficient_funds:
            response_status = status.HTTP_402_PAYMENT_REQUIRED

        return Response(data, status=response_status)

    @staticmethod
    def _get_account_from_card_id(card_uuid) -> SociBankAccount:
        soci_bank_account = get_object_or_404(queryset=SociBankAccount.objects.all(), card_uuid=card_uuid)

        return soci_bank_account


class ChargeSociBankAccountView(CustomCreateAPIView):
    """
    Charges the specified account for the total amount of the products associated with provided SKU numbers.
    If the SKU is the direct charge, a direct charge amount needs to be provided as well.
    """
    deserializer_class = ChargeSociBankAccountDeserializer
    serializer_class = PurchaseSerializer

    @swagger_auto_schema(
        request_body=deserializer_class(many=True),
        operation_summary="Charge SociBankAccount",
        manual_parameters=[Parameter(
            name='card-number', in_=IN_HEADER, description="The RFID card id connected to a user's Soci bank account",
            type=TYPE_INTEGER, required=True
        )],
        responses={
            "201": serializer_class,
            "400": ": Illegal input",
            "402": ": This SociBankAccount cannot be charged due to insufficient funds",
            "404": ": Could not retrieve SociBankAccount from the provided card number",
        },
    )
    def post(self, request, *args, **kwargs):
        card_uuid = self.request.META.get('HTTP_CARD_NUMBER', None)
        soci_bank_account: SociBankAccount = self._get_account_from_card_id(card_uuid=card_uuid)

        deserializer = self.get_deserializer(
            data=request.data, context={'soci_bank_account': soci_bank_account}, many=True, allow_empty=False)
        deserializer.is_valid(raise_exception=True)

        purchase = Purchase.objects.create(source=soci_bank_account, signed_off_by=request.user)
        deserializer.save(purchase=purchase)
        purchase.save()  # Trigger signal

        serializer = self.get_serializer(purchase)
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)

    @staticmethod
    def _get_account_from_card_id(card_uuid) -> SociBankAccount:
        soci_bank_account = get_object_or_404(queryset=SociBankAccount.objects.all(), card_uuid=card_uuid)

        return soci_bank_account
