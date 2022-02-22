from django.db import models
from django.utils.translation import ugettext_lazy as _


class InternalGroupPositionMembershipType(models.TextChoices):
    FUNCTIONARY = "functionary", _("Functionary")
    ACTIVE_FUNCTIONARY_PANG = "active-functionary-pang", _("Active functionary pang")
    OLD_FUNCTIONARY_PANG = "old-functionary-pang", _("Old functionary pang")
    GANG_MEMBER = "gang-member", _("Gang member")
    ACTIVE_GANG_MEMBER_PANG = "active-gang-member-pang", _("Active gang member pang")
    OLD_GANG_MEMBER_PANG = "old-gang-member-pang", _("Old gang member pang")
    INTEREST_GROUP_MEMBER = "interest-group-member", _("Interest group member")
    HANGAROUND = "hangaround", _("Hangaround")
    TEMPORARY_LEAVE = "temporary-leave", _("Temporary leave")
