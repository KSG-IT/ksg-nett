import graphene
from graphene import Node
from graphene_django import DjangoObjectType
from graphene_django_cud.mutations import (
    DjangoPatchMutation,
    DjangoDeleteMutation,
    DjangoCreateMutation,
)
from graphene_django import DjangoConnectionField

from sensors.models import SensorMeasurement


class SensorMeasurementNode(DjangoObjectType):
    class Meta:
        model = SensorMeasurement
        interfaces = (Node,)

    @classmethod
    def get_node(cls, info, id):
        return SensorMeasurement.objects.get(pk=id)


class SensorMeasurementQuery(graphene.ObjectType):
    sensor_measurement = Node.Field(SensorMeasurementNode)
    all_sensor_measurements = DjangoConnectionField(SensorMeasurementNode)

    def resolve_all_sensor_measurements(self, info, *args, **kwargs):
        return SensorMeasurement.objects.all()


class CreateSensorMeasurementMutation(DjangoCreateMutation):
    class Meta:
        model = SensorMeasurement


class PatchSensorMeasurementMutation(DjangoPatchMutation):
    class Meta:
        model = SensorMeasurement


class DeleteSensorMeasurementMutation(DjangoDeleteMutation):
    class Meta:
        model = SensorMeasurement


class SensorsMutations(graphene.ObjectType):
    create_sensor_measurement = CreateSensorMeasurementMutation.Field()
    patch_sensor_measurement = PatchSensorMeasurementMutation.Field()
    delete_sensor_measurement = DeleteSensorMeasurementMutation.Field()
