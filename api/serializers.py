from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from commissions.models import Commission
from users.models import User


# ===============================
# COMMISSIONS
# ===============================

class CommissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commission
        fields = ['id', 'name', 'holders']


class CreateCommissionSerializer(serializers.ModelSerializer):
    name = serializers.CharField(required=True, validators=[
        UniqueValidator(queryset=Commission.objects.all(), message='Commission already exists.')])

    class Meta:
        model = Commission
        fields = '__all__'


# ===============================
# USERS
# ===============================


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'id', 'username', 'email')
