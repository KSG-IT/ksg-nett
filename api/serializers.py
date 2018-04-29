from django.conf import settings
from rest_framework import serializers

from api.exceptions import InsufficientFundsException
from economy.models import SociProduct, Transaction, SociBankAccount


# ===============================
# ECONOMY
# ===============================

class SociProductSerializer(serializers.Serializer):
    sku_number = serializers.CharField(read_only=True, label="Product SKU number")

    name = serializers.CharField(read_only=True, label="Product name")

    price = serializers.IntegerField(read_only=True, label="Product price in NOK")

    description = serializers.CharField(read_only=True, allow_blank=True, allow_null=True, label="Product description",
                                        help_text="Returns `null` if no description exists")

    icon = serializers.CharField(read_only=True, label="Product icon descriptor")


class CheckBalanceSerializer(serializers.Serializer):
    user = serializers.CharField(read_only=True, label="User´s full name")

    balance = serializers.IntegerField(source='public_balance', read_only=True, allow_null=True, label="Balance in NOK",
                                       help_text="Returns `null` if user has disabled public display of balance")

    has_sufficient_funds = serializers.BooleanField(read_only=True,
                                                    label="Whether the user has enough funds left to charge or not")


class ChargeSociBankAccountDeserializer(serializers.Serializer):
    sku = serializers.CharField(label="Product SKU number to charge for")

    amount = serializers.IntegerField(required=False, label="Amount to charge",
                                      help_text="Only required when using the SKU for charging a direct amount")

    @staticmethod
    def validate_sku(value):
        if not SociProduct.objects.filter(sku_number=value).exists():
            raise serializers.ValidationError('SKU number is invalid.')
        return value

    @staticmethod
    def validate_amount(value):
        if value <= 0:
            raise serializers.ValidationError('Amount must be positive.')
        return value

    def validate(self, attrs):
        if attrs.get('sku', None) != settings.DIRECT_CHARGE_SKU:
            if attrs.get('amount', None):
                raise serializers.ValidationError('Amount can only be set when charging a direct amount.')

            attrs['amount'] = SociProduct.objects.get(sku_number=attrs['sku']).price

        elif attrs.get('sku', None) == settings.DIRECT_CHARGE_SKU and attrs.get('amount', None) is None:
            raise serializers.ValidationError('Amount must be set when charging a direct amount.')

        if attrs['amount'] > self.instance.balance:
            raise InsufficientFundsException()

        return attrs

    def update(self, instance: SociBankAccount, validated_data):
        destination = SociBankAccount.objects.get(card_uuid=settings.SOCI_CARD_ID)
        product = SociProduct.objects.get(sku_number=validated_data['sku'])
        transaction = Transaction.objects.create(source=instance, destination=destination,
                                                 amount=validated_data['amount'], product=product,
                                                 signed_off_by=self.context['user'])

        return transaction


class TransactionSerializer(serializers.Serializer):
    amount_charged = serializers.IntegerField(read_only=True, source='amount',
                                              label="Amount that was charged from user´s Soci account")

    amount_remaining = serializers.IntegerField(read_only=True, source='source.public_balance', allow_null=True,
                                                label="Remaining balance in user´s Soci account",
                                                help_text="Returns `null` if user has disabled public display of "
                                                          "balance")

    product_purchased = serializers.CharField(read_only=True, source='product.name',
                                              label="The product that was purchased")
