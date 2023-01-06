import graphene


class InternalGroupPositionTypeEnum(graphene.Enum):
    FUNCTIONARY = "functionary"
    ACTIVE_FUNCTIONARY_PANG = "active-functionary-pang"
    OLD_FUNCTIONARY_PANG = "old-functionary-pang"
    GANG_MEMBER = "gang-member"
    ACTIVE_GANG_MEMBER_PANG = "active-gang-member-pang"
    OLD_GANG_MEMBER_PANG = "old-gang-member-pang"
    INTEREST_GROUP_MEMBER = "interest-group-member"
    HANGAROUND = "hangaround"
    TEMPORARY_LEAVE = "temporary-leave"
