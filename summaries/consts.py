# coding: utf-8
from django.db import models


class SummaryType(models.TextChoices):
    OTHER = ("annet", "Annet")
    KAFE_ANSVARLIG = ("kafeansvarlig", "Kafeansvarlig")
    HOVMESTER = ("hovmester", "Hovmester")
    BARSJEF = ("barsjef", "Barsjef")
    SOUSCHEF = ("souschef", "Souschef")
    ARRANGEMENT = ("arrangement", "Arrangement")
    OKONOMI = ("okonomi", "Økonomi")
    STYRET = ("styret", "Styret")
    DRIFT = ("drift", "Drift")
    DAGLIGHALLEN = ("daglighallen", "Daglighallen")
    KSG_IT = ("kit", "KSG-IT")
