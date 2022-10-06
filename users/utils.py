def membership_list_helper(membership_query):
    from graphql_relay import to_global_id

    from common.util import get_semester_year_shorthand
    from users.schema import ManageInternalGroupUserObject

    membership_list = []
    for membership in membership_query:
        membership_list.append(
            ManageInternalGroupUserObject(
                user_id=to_global_id("UserNode", membership.user.id),
                full_name=membership.user.get_full_name(),
                internal_group_position_membership=membership,
                internal_group_position_type=membership.type,
                position_name=membership.position.name,
                date_joined_semester_shorthand=get_semester_year_shorthand(
                    membership.date_joined
                ),
            )
        )
    return membership_list
