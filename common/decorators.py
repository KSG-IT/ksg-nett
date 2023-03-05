from functools import wraps
from typing import Callable
from django.core.exceptions import PermissionDenied
from twisted.mail._except import IllegalOperation

from .models import FeatureFlag


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


def gql_login_required(
    fail_to_none: bool = False,
    fail_message: str = "You are not permitted to view this",
    fail_to_lambda=None,
):
    """
    gql_login_required is a function which wraps a `resolve_<x>` or
    `mutate` field for any GraphQL object.
    :param fail_to_none: If true, and the user is not authorized, the field will resolve to None.
                            If false, the entire query will fail dramatically in a 401.
    :param fail_message: If fail_to_none is false, and the permission fails, this variable determines
                         the string which is thrown in the exception.
    :param fail_to_lambda: If not none, and the permission fails, this variable (assumed to be a function)
                           will be called.
    :return:
    """

    def decorator(func):
        @wraps(func)
        def wrapper(cls, info, *args, **kwargs):
            if not hasattr(info, "context") or not hasattr(info.context, "user"):
                if fail_to_lambda:
                    return fail_to_lambda()
                elif fail_to_none:
                    return None
                else:
                    raise PermissionDenied(fail_message)

            user = info.context.user
            if not user.is_authenticated:
                if fail_to_lambda:
                    return fail_to_lambda()
                elif fail_to_none:
                    return None
                else:
                    raise PermissionDenied(fail_message)
            return func(cls, info, *args, **kwargs)

        return wrapper

    return decorator


def view_feature_flag_required(
    feature_flag_name: str,
    fail_to_none: bool = False,
    fail_message: str = "Feature flag is not enabled",
):
    def decorator(func):
        @wraps(func)
        def wrapper(request, *args, **kwargs):
            feature_flag, _ = FeatureFlag.objects.get_or_create(name=feature_flag_name)
            if not feature_flag.enabled:
                if fail_to_none:
                    return None
                else:
                    raise IllegalOperation(fail_message)

            return func(request, *args, **kwargs)

        return wrapper

    return decorator


def gql_feature_flag_required(
    feature_flag_name: str,
    fail_to_none: bool = False,
):
    def decorator(func):
        @wraps(func)
        def wrapper(cls, info, *args, **kwargs):
            feature_flag, _ = FeatureFlag.objects.get_or_create(name=feature_flag_name)
            if not feature_flag.enabled:
                if fail_to_none:
                    return None
                else:
                    raise IllegalOperation(
                        f"Feature flag {feature_flag_name} is not enabled"
                    )

            return func(cls, info, *args, **kwargs)

        return wrapper

    return decorator
