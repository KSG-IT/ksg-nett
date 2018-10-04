from drf_yasg import openapi
from drf_yasg.openapi import Contact
from drf_yasg.views import get_schema_view
from rest_framework import generics, status
from rest_framework import permissions
from rest_framework.generics import get_object_or_404, ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from api.serializers import CheckBalanceSerializer, SociProductSerializer, ChargeSociBankAccountDeserializer, \
    PurchaseSerializer
from economy.models import SociBankAccount, SociProduct, Purchase

# ===============================
# API DOCS
# ===============================

schema_view = get_schema_view(
    urlconf='ksg_nett.urls',
    info=openapi.Info(
        title="KSG-nett API",
        default_version='v1',
        description="### This is the API reference for the web services of Kafé- og Serveringsgjengen at Samfundet.",
        contact=Contact(name="Maintained by KSG-IT", email="ksg-it@samfundet.no")
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)


# ===============================
# ECONOMY
# ===============================

class SociProductsView(ListAPIView):
    """
    #### Retrieves a list of products that can be purchased at Soci, consisting of name and price.
    """
    serializer_class = SociProductSerializer

    def get(self, request, *args, **kwargs):
        soci_products = SociProduct.objects.all()
        serializer = self.get_serializer(soci_products, many=True)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)


class CheckBalanceView(RetrieveAPIView):
    """
    #### Checks the available balance for an account, based on the provided RFID card number. \
    If the card id was found, returns user's full name and balance status, as well as balance \
    amount if user has enabled this in settings.
    """
    serializer_class = CheckBalanceSerializer

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


class ChargeSociBankAccountView(generics.CreateAPIView):
    """
    #### Charges the specified account, based on the provided RFID card number, \
    for the price of the product with provided SKU number. \
    If the SKU is the direct charge, an amount needs to be specified as well.
    """
    serializer_class = PurchaseSerializer

    def post(self, request, *args, **kwargs):
        card_uuid = self.request.META.get('HTTP_CARD_NUMBER', None)
        soci_bank_account: SociBankAccount = self._get_account_from_card_id(card_uuid=card_uuid)

        deserializer = ChargeSociBankAccountDeserializer(
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
