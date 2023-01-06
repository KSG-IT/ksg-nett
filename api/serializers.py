from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainSlidingSerializer

from api.exceptions import InsufficientFundsException, NoSociSessionError
from economy.models import SociProduct, ProductOrder, SociSession, SociBankAccount


class CustomTokenObtainSlidingSerializer(TokenObtainSlidingSerializer):
    """
    Overridden so we can obtain a token for a user based only on the card uuid.
    """

    username_field = "card_uuid"

    def __init__(self, *args, **kwargs):
        """
        Overridden from `TokenObtainSerializer` since this adds a required
        field `password` to the serializer that we don't need.
        """
        super().__init__(*args, **kwargs)
        del self.fields["password"]

    def validate(self, attrs):
        """
        Overridden from `TokenObtainSlidingSerializer` since
        this expects a username and password to be supplied.
        """
        data = {}

        token = self.get_token(self.context["request"].user)

        data["token"] = str(token)

        return data


# ===============================
# ECONOMY
# ===============================
from sensors.consts import MEASUREMENT_TYPE_CHOICES
from sensors.models import SensorMeasurement


class SociProductSerializer(serializers.Serializer):
    sku_number = serializers.CharField(read_only=True, label="Product SKU number")

    name = serializers.CharField(read_only=True, label="Product name")

    price = serializers.IntegerField(read_only=True, label="Product price in NOK")

    description = serializers.CharField(
        read_only=True,
        allow_blank=True,
        allow_null=True,
        label="Product description",
        help_text="Returns `null` if no description exists",
    )

    icon = serializers.CharField(read_only=True, label="Product icon descriptor")


class CheckBalanceSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True, label="This soci bank account ID")

    user = serializers.CharField(
        source="user.get_full_name", read_only=True, label="User´s full name"
    )

    balance = serializers.IntegerField(
        read_only=True,
        label="Balance in NOK",
        help_text="Should not be displayed publicly",
    )
    soci_gold = serializers.BooleanField(
        source="is_gold", read_only=True, label="Soci gold status", default=False
    )


class ChargeSociBankAccountDeserializer(serializers.Serializer):
    sku = serializers.CharField(label="Product SKU number to charge for")

    order_size = serializers.IntegerField(
        default=1,
        required=False,
        label="Order size for this product",
        help_text="Defaults to 1 if not supplied",
    )

    @staticmethod
    def validate_sku(value):
        if not SociProduct.objects.filter(sku_number=value).exists():
            raise serializers.ValidationError("SKU number is invalid.")
        return value

    @staticmethod
    def validate_order_size(value):
        if value <= 0:
            raise serializers.ValidationError("Order size must be positive.")
        return value

    def validate(self, attrs):
        if attrs["sku"] != settings.DIRECT_CHARGE_SKU:
            attrs["amount"] = SociProduct.objects.get(sku_number=attrs["sku"]).price
        else:
            attrs["amount"] = 1

        self.context["total"] += attrs["amount"] * attrs["order_size"]
        if self.context["total"] > self.context["soci_bank_account"].balance:
            raise InsufficientFundsException()

        if SociSession.get_active_session() is None:
            raise NoSociSessionError()

        return attrs

    def create(self, validated_data):
        product_order = ProductOrder.objects.create(
            product=SociProduct.objects.get(sku_number=validated_data.pop("sku")),
            **validated_data
        )

        return product_order


class PurchaseSerializer(serializers.Serializer):
    amount_charged = serializers.IntegerField(
        read_only=True,
        source="total_amount",
        label="Amount that was charged from user´s Soci account",
    )

    amount_remaining = serializers.IntegerField(
        read_only=True,
        source="source.balance",
        label="Remaining balance in user´s Soci account",
        help_text="Should not be displayed publicly",
    )

    products_purchased = serializers.ListField(
        read_only=True,
        child=serializers.CharField(),
        help_text="The products that were purchased",
    )


class SensorMeasurementSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=MEASUREMENT_TYPE_CHOICES,
        label="The type of measurement.",
    )
    value = serializers.FloatField(
        label="The value of the measurement",
    )
    created_at = serializers.DateTimeField(
        label="The time of the measurement",
    )

    def create(self, validated_data):
        return SensorMeasurement.objects.create(**validated_data)
