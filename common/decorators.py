from functools import wraps
from typing import Callable
from django.core.exceptions import PermissionDenied


def _handle_not_permitted(
    fail_to_none: bool = False,
    fail_message: str = "You do not have permission to do this",
    fail_to_lambda: Callable = None,
):
    if fail_to_lambda:
        return fail_to_lambda()
    elif fail_to_none:
        return None
    else:
        raise PermissionDenied(fail_message)


def gql_has_permissions(
    *permissions,
    fail_to_none: bool = False,
    fail_message: str = "You do not have permission to do this",
    fail_to_lambda=None,
    require_superuser=False,
):
    """
    :param permissions: The permission required to access the wrapped resource.
    :param fail_to_none: If true, and the user is not authorized, the field will resolve to None.
                            If false, the entire query will fail dramatically in a 401.
    :param fail_message: If fail_to_none is false, and the permission fails, this variable determines
                         the string which is thrown in the exception.
    :param fail_to_lambda: If not none, and the permission fails, this variable (assumed to be a function)
                           will be called.
    :param require_superuser: If true, the user muse be a superuser.
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(cls, info, *args, **kwargs):
            if not hasattr(info, "context") or not hasattr(info.context, "user"):
                return _handle_not_permitted(fail_to_none, fail_message, fail_to_lambda)

            if require_superuser:
                if not info.context.user.is_superuser:
                    return _handle_not_permitted(
                        fail_to_none, fail_message, fail_to_lambda
                    )

            user = info.context.user
            if not user and len(permissions) > 0 or not user.has_perms(permissions):
                return _handle_not_permitted(fail_to_none, fail_message, fail_to_lambda)

            return func(cls, info, *args, **kwargs)

        return wrapper

    return decorator
