# coding: utf-8

SUMMARY_TYPE_OTHER = 'other'
SUMMARY_TYPE_KAFE_ANSVARLIG = 'kafeansvarlig'
SUMMARY_TYPE_HOVMESTER = 'hovmester'
SUMMARY_TYPE_BARSJEF = 'barsjef'
SUMMARY_TYPE_SOUSCHEF = 'souschef'
SUMMARY_TYPE_ARRANGEMENT = 'arrangement'
SUMMARY_TYPE_OKONOMI = 'okonomi'
SUMMARY_TYPE_STYRET = 'styret'
SUMMARY_TYPE_KSG_IT = 'kit'

SUMMARY_TYPE_CHOICES = (
    (SUMMARY_TYPE_OTHER, 'Other summary'),
    (SUMMARY_TYPE_KAFE_ANSVARLIG, 'Kafeansvarlig summary'),
    (SUMMARY_TYPE_HOVMESTER, 'Hovmester summary'),
    (SUMMARY_TYPE_BARSJEF, 'Barsjef summary'),
    (SUMMARY_TYPE_SOUSCHEF, 'Souschef summary'),
    (SUMMARY_TYPE_ARRANGEMENT, 'Arrangement summary'),
    (SUMMARY_TYPE_OKONOMI, 'Økonomi summary'),
    (SUMMARY_TYPE_STYRET, 'Styret summary'),
    (SUMMARY_TYPE_KSG_IT, 'KSG-IT summary')
)

SUMMARY_TYPE_CHOICES_DICT = dict(SUMMARY_TYPE_CHOICES)
