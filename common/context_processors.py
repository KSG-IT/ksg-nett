from organization.models import InternalGroup


def internal_groups(request):
    groups = InternalGroup.objects.filter(type=InternalGroup.Type.INTERNAL_GROUP).order_by("name")
    return {"header_internal_groups": groups}  # we prefix it header_ so it does not conflict in the organization/internalgroups/<id> view 
