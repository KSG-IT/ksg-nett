from django.db import models
from django.utils.translation import ugettext_lazy as _


class InternalGroups(models.TextChoices):
    EDGAR = 'edgar', _('Edgar')
    LYCHE_BAR = 'lyche-bar', _('Lyche Bar')
    LYCHE_KITCHEN = 'lyche-kitchen', _('Lyche Kjøkken')
    BAR = 'bar', _('Bar')
    SPRIT = 'sprit', _('Spritgjengen')
    ARRANGEMENT = 'arrangement', _('Arrangement')
    DAGLIGHALLEN = 'daglighallen', _('Daglighallen Bar')

