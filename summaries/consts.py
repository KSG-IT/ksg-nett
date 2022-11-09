# coding: utf-8
from django.db import models


class SummaryType(models.TextChoices):
    OTHER = ("ANNET", "Annet")
    KAFE_ANSVARLIG = ("KAFEANSVARLIG", "Kafeansvarlig")
    HOVMESTER = ("HOVMESTER", "Hovmester")
    BARSJEF = ("BARSJEF", "Barsjef")
    SPRITBARSJEF = ("SPRITBARSJEF", "Spritbarsjef")
    SOUSCHEF = ("SOUSCHEF", "Souschef")
    ARRANGEMENT = ("ARRANGEMENT", "Arrangement")
    OKONOMI = ("OKONOMI", "Økonomi")
    STYRET = ("STYRET", "Styret")
    DRIFT = ("DRIFT", "Drift")
    DAGLIGHALLEN = ("DAGLIGHALLEN", "Daglighallen")
    KSG_IT = ("KIT", "KSG-IT")
