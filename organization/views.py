from django.contrib.auth.decorators import login_required
from django.shortcuts import render, HttpResponse
from organization.models import InternalGroup
from rest_framework import status


@login_required
def internal_group(request, internal_group_id):
    if request.method == "GET":
        try:
            internal_group = InternalGroup.objects.get(pk=internal_group_id)
        except InternalGroup.DoesNotExist:
            return render(request, template_name="internal/not_found.html")

        all_internal_groups = InternalGroup.objects.filter(type=InternalGroup.Type.INTERNAL_GROUP).order_by("name")
        all_interest_groups = InternalGroup.objects.filter(type=InternalGroup.Type.INTEREST_GROUP).order_by("name")
        ctx = {  # The context returns a list structure of groups the template can loop over to display in the sidebar
            "group_overview": [
                {
                    "title": InternalGroup.Type.INTERNAL_GROUP.label,
                    "groups": all_internal_groups
                },
                {
                    "title": InternalGroup.Type.INTEREST_GROUP.label,
                    "groups": all_interest_groups
                },
            ],
            "internal_group": internal_group,
        }
        return render(request, template_name="organization/internal_groups.html", context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
