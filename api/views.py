import jwt
from django.utils import timezone
from drf_yasg.openapi import Parameter, IN_QUERY, TYPE_STRING
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404, DestroyAPIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainSlidingView, TokenRefreshSlidingView, TokenVerifyView

from api.serializers import CheckBalanceSerializer, SociProductSerializer, ChargeSociBankAccountDeserializer, \
    PurchaseSerializer
from api.view_mixins import CustomCreateAPIView
from economy.models import SociBankAccount, SociProduct, Purchase, SociSession


class CustomTokenObtainSlidingView(TokenObtainSlidingView):
    swagger_schema = None

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        self._start_new_soci_session(token=response.data['token'])
        return response

    @staticmethod
    def _start_new_soci_session(token):
        # In case XApp was hindered from terminating the active session manually,
        # we terminate any currently active session before starting a new one.
        SociSession.terminate_active_session()

        card_user_id = jwt.decode(token, verify=False)['user_id']
        SociSession.objects.create(signed_off_by_id=card_user_id)


class CustomTokenRefreshSlidingView(TokenRefreshSlidingView):
    swagger_schema = None


class CustomTokenVerifyView(TokenVerifyView):
    swagger_schema = None


class TerminateSociSessionView(DestroyAPIView):
    """
    Terminates the current SociSession by setting an end date.
    """

    @swagger_auto_schema(
        tags=['Soci Sessions'],
        operation_summary="Terminate SociSession",
        responses={'200': ''}
    )
    def delete(self, request, *args, **kwargs):
        SociSession.terminate_active_session()

        return Response(status=status.HTTP_200_OK)


class SociProductListView(ListAPIView):
    """
    Retrieves a list of products that can be purchased at Soci.
    """
    serializer_class = SociProductSerializer
    queryset = SociProduct.objects.all()

    @swagger_auto_schema(
        tags=['Soci Products'],
        operation_summary="List SociProducts"
    )
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        soci_products = (
            self.get_queryset()
                .exclude(end__lt=now)
                .exclude(start__gt=now)
                .order_by('sku_number')
        )
        serializer = self.get_serializer(soci_products, many=True)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)


class SociBankAccountBalanceDetailView(RetrieveAPIView):
    """
    Checks the available balance of an account, based on the provided RFID card number.
    """
    queryset = SociBankAccount.objects.all()
    serializer_class = CheckBalanceSerializer

    @swagger_auto_schema(
        tags=['Soci Bank Accounts'],
        operation_summary="Retrieve SociBankAccount balance",
        manual_parameters=[Parameter(
            name='card_uuid',
            in_=IN_QUERY,
            description="The RFID card id connected to a user's Soci bank account",
            type=TYPE_STRING,
            required=True
        )],
        responses={
            "404": ": Could not retrieve SociBankAccount from the provided card number",
        },
    )
    def get(self, request, *args, **kwargs):
        soci_bank_account = self.get_object()
        serializer = self.get_serializer(soci_bank_account)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)

    def get_object(self) -> SociBankAccount:
        card_uuid = self.request.query_params.get('card_uuid', None)
        if card_uuid is None:
            raise ValidationError("You need to provide a card uuid as a query parameter.")

        return get_object_or_404(queryset=self.get_queryset(), card_uuid=card_uuid)


class SociBankAccountChargeView(CustomCreateAPIView):
    """
    Charges the specified account for the total amount of the products associated with provided SKU numbers.
    If the SKU is the direct charge, a direct charge amount needs to be provided as well.
    """
    queryset = SociBankAccount.objects.all()
    lookup_url_kwarg = 'id'
    deserializer_class = ChargeSociBankAccountDeserializer
    serializer_class = PurchaseSerializer

    @swagger_auto_schema(
        tags=['Soci Bank Accounts'],
        request_body=deserializer_class(many=True),
        operation_summary="Charge SociBankAccount",
        responses={
            "201": serializer_class,
            "400": ": Illegal input",
            "402": ": This SociBankAccount cannot be charged due to insufficient funds",
            "404": ": Could not retrieve SociBankAccount from the provided card number",
        },
    )
    def post(self, request, *args, **kwargs):
        soci_bank_account: SociBankAccount = self.get_object()

        deserializer = self.get_deserializer(
            data=request.data, context={'soci_bank_account': soci_bank_account}, many=True, allow_empty=False)
        deserializer.is_valid(raise_exception=True)

        purchase = Purchase.objects.create(source=soci_bank_account)
        deserializer.save(purchase=purchase)

        serializer = self.get_serializer(purchase)
        data = serializer.data

        return Response(data, status=status.HTTP_201_CREATED)
