import jwt
from django.db import DatabaseError, transaction
from django.utils import timezone
from drf_yasg.openapi import Parameter, IN_QUERY, TYPE_STRING
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, permissions, generics
from rest_framework.exceptions import ValidationError
from rest_framework.generics import (
    ListAPIView,
    RetrieveAPIView,
    get_object_or_404,
    DestroyAPIView,
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (
    TokenObtainSlidingView,
    TokenRefreshSlidingView,
    TokenVerifyView,
)

from api.models import PurchaseTransactionLogEntry, BlacklistedSong
from api.permissions import SensorTokenPermission
from api.serializers import (
    CheckBalanceSerializer,
    SociProductSerializer,
    SensorMeasurementSerializer,
    CustomTokenObtainSlidingSerializer,
    BlacklistedSongSerializer,
)
from economy.price_strategies import calculate_stock_price_for_product

from sensors.consts import MEASUREMENT_TYPE_TEMPERATURE, MEASUREMENT_TYPE_CHOICES
from sensors.models import SensorMeasurement
from api.view_mixins import CustomCreateAPIView
from economy.models import SociBankAccount, SociProduct, SociSession, ProductOrder
from ksg_nett.custom_authentication import CardNumberAuthentication
from django.conf import settings
from common.util import check_feature_flag


class CustomTokenObtainSlidingView(TokenObtainSlidingView):
    swagger_schema = None
    serializer_class = CustomTokenObtainSlidingSerializer
    authentication_classes = [CardNumberAuthentication]
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        self._start_new_soci_session(token=response.data["token"])
        return response

    @staticmethod
    def _start_new_soci_session(token):
        # In case XApp was hindered from terminating the active session manually,
        # we terminate any currently active session before starting a new one.
        SociSession.terminate_active_session()

        card_user_id = jwt.decode(
            token,
            settings.AUTH_JWT_SECRET,
            algorithms=settings.AUTH_JWT_METHOD,
            options={
                "verify_signature": False,
            },
        )["user_id"]
        SociSession.objects.create(created_by_id=card_user_id)


class CustomTokenRefreshSlidingView(TokenRefreshSlidingView):
    swagger_schema = None


class CustomTokenVerifyView(TokenVerifyView):
    swagger_schema = None


class TerminateSociSessionView(DestroyAPIView):
    """
    Terminates the current SociSession by setting an end date.
    """

    @swagger_auto_schema(
        tags=["Soci Sessions"],
        operation_summary="Terminate SociSession",
        responses={"200": ""},
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

    @swagger_auto_schema(tags=["Soci Products"], operation_summary="List SociProducts")
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        soci_products = (
            self.get_queryset()
            .exclude(hide_from_api=True)
            .exclude(end__lt=now)
            .exclude(start__gt=now)
            .order_by("price")
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
        tags=["Soci Bank Accounts"],
        operation_summary="Retrieve SociBankAccount balance",
        manual_parameters=[
            Parameter(
                name="card_uuid",
                in_=IN_QUERY,
                description="The RFID card id connected to a user's Soci bank account",
                type=TYPE_STRING,
                required=True,
            )
        ],
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
        card_uuid = self.request.query_params.get("card_uuid", None)
        if card_uuid is None:
            raise ValidationError(
                "You need to provide a card uuid as a query parameter."
            )

        return get_object_or_404(queryset=self.get_queryset(), card_uuid=card_uuid)


class SensorMeasurementView(CustomCreateAPIView, generics.ListAPIView):
    serializer_class = SensorMeasurementSerializer
    deserializer_class = SensorMeasurementSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [SensorTokenPermission()]

        return []

    def get_queryset(self):
        # We don't really bother to validate this input. A bad input will just
        # return 0 results.
        type = self.request.query_params.get("type", MEASUREMENT_TYPE_TEMPERATURE)
        return SensorMeasurement.objects.filter(
            type=type, created_at__gte=timezone.now() - timezone.timedelta(days=1)
        )

    @swagger_auto_schema(
        request_body=deserializer_class(many=True),
        operation_summary="Create measurements",
        responses={
            "201": serializer_class(many=True),
            "400": ": Illegal input.",
            "403": ": You are not authorized to create measurements.",
        },
    )
    def post(self, request: Request, *args, **kwargs):
        deserializer = self.get_deserializer(data=request.data, many=True, context={})
        deserializer.is_valid(raise_exception=True)
        deserializer.save()

        # Try to clear out old entries.
        try:
            SensorMeasurementView._remove_old_measurement_instances()
        except DatabaseError:
            # Should we do something?
            pass

        return Response(deserializer.data, status=status.HTTP_201_CREATED)

    @swagger_auto_schema(
        operation_summary="Get measurement data for the last 24 hours.",
        manual_parameters=[
            Parameter(
                name="type",
                in_=IN_QUERY,
                default="temperature",
                description=f"The type of measurements.",
                type=TYPE_STRING,
                enum=[x[0] for x in MEASUREMENT_TYPE_CHOICES],
                required=False,
            )
        ],
        responses={
            "200": serializer_class(many=True),
        },
    )
    def get(self, request: Request, *args, **kwargs):
        measurements = self.get_queryset()
        serializer = self.get_serializer(measurements, many=True)
        data = serializer.data

        return Response(data, status=status.HTTP_200_OK)

    @staticmethod
    def _remove_old_measurement_instances():
        SensorMeasurement.objects.filter(
            created_at__lte=timezone.now() - timezone.timedelta(days=1)
        ).delete()


class ChargeBankAccountView(APIView):
    def post(self, request, *args, **kwargs):
        order = request.data
        bank_account_id = order["bank_account_id"]

        session = SociSession.get_active_session()
        if session is None:
            return Response(
                {"message": "No active SociSession"}, status=status.HTTP_400_BAD_REQUEST
            )

        account = SociBankAccount.objects.get(id=bank_account_id)
        orders = []
        for product_order in order["products"]:
            sku_number = product_order["sku"]
            product = SociProduct.objects.filter(sku_number=sku_number).first()
            if product is None:
                return Response(
                    {"message": f"Invalid product sku '{sku_number}' in order"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            order_size = product_order["order_size"]

            if (
                check_feature_flag(settings.X_APP_AUCTION_MODE, fail_silently=True)
                and product.purchase_price
            ):  # Stock mode is enabled and the product has a registered purchase price
                product_price = calculate_stock_price_for_product(product.id)
            else:
                product_price = product.price

            orders.append(
                ProductOrder(
                    product=product,
                    order_size=product_order["order_size"],
                    cost=order_size * product_price,
                    source=account,
                    session=session,
                )
            )

        total_cost = sum([order.cost for order in orders])

        if not total_cost:
            raise RuntimeError("Could not determine purchase cost")

        if account.balance < total_cost and not account.is_gold:
            return Response(
                {"message": "Insufficient funds"}, status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            account.remove_funds(total_cost)
            for order in orders:
                order.save()

            PurchaseTransactionLogEntry.objects.create(
                user=account.user,
                amount=total_cost,
                transaction_source=PurchaseTransactionLogEntry.TransactionSourceOptions.API,
            )

        return Response(status=status.HTTP_200_OK)


class BlacklistedSongsListView(ListAPIView):
    """
    Retrieves a list of ids that are blacklisted from the Soci jukebox.
    """

    serializer_class = BlacklistedSongSerializer
    queryset = BlacklistedSong.objects.all()

    @swagger_auto_schema(
        tags=["Blacklisted songs"], operation_summary="List Blacklisted songs"
    )
    def get(self, request, *args, **kwargs):
        now = timezone.now()
        blacklisted_songs = self.get_queryset().filter(blacklisted_until__gte=now)

        serializer = self.get_serializer(blacklisted_songs, many=True)
        data = blacklisted_songs.values_list("spotify_song_id", flat=True)

        return Response(data, status=status.HTTP_200_OK)
