from rest_framework import generics, status
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.serializers import UserSerializer, CommissionSerializer, CreateCommissionSerializer
from commissions.models import Commission
from users.models import User


# ===============================
# COMMISSIONS
# ===============================

class ListCommissionsView(generics.ListAPIView):
    """
    Returns all available commission in the database, as well as the IDs of all users holding it
    """
    model = Commission
    permission_classes = [IsAuthenticated]
    serializer_class = CommissionSerializer
    queryset = Commission.objects.all()

    def get(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)


class CreateCommissionView(generics.CreateAPIView):
    """
    Create a new commission in the database.
    """
    model = Commission
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCommissionSerializer
    queryset = Commission.objects.all()

    def post(self, request, *args, **kwargs):
        self.check_permissions(request)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        commission = serializer.save()
        data = CommissionSerializer(commission).data

        return Response(data, status.HTTP_201_CREATED)


class UpdateCommissionView(generics.UpdateAPIView):
    """
    Updating an existing commission in the database.
    """
    model = Commission
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCommissionSerializer
    lookup_url_kwarg = 'commission_id'
    queryset = Commission.objects.all()

    def patch(self, request, *args, **kwargs):
        commission = self.get_object()
        serializer = self.get_serializer(commission, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        data = CommissionSerializer(commission).data

        return Response(data, status=status.HTTP_201_CREATED)


class DeleteCommissionView(generics.DestroyAPIView):
    """
    Deleting an existing commission in the database.
    """
    model = Commission
    permission_classes = [IsAuthenticated]
    serializer_class = CreateCommissionSerializer
    lookup_url_kwarg = 'commission_id'
    queryset = Commission.objects.all()

    def delete(self, request, *args, **kwargs):
        commission = self.get_object()
        commission.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# ===============================
# USERS
# ===============================

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-id')
    serializer_class = UserSerializer
