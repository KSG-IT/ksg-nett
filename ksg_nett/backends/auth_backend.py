class UserTypeBackend:
    def authenticate(self, request, username=None, password=None):
        return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        Checks if a user has a permission through his/her types.
        """

        if not hasattr(user_obj, "user_types"):
            return False

        return perm in self.get_all_permissions(user_obj)

    def get_all_permissions(self, user_obj, obj=None):
        """
        Returns the set of permission strings matching a users types.
        :param user_obj:
        :return:
        """
        perms = set()
        if not hasattr(user_obj, "user_types"):
            return perms

        for type in user_obj.user_types.all():
            perms = perms.union(
                {
                    "{}.{}".format(app_label, codename)
                    for app_label, codename in type.permissions.values_list(
                        "content_type__app_label", "codename"
                    )
                }
            )

        return perms
