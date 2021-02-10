from django.contrib.auth.decorators import login_required
from django.shortcuts import render, HttpResponse, get_object_or_404, reverse, redirect
from organization.models import InternalGroup
from organization.forms import InternalGroupForm
from rest_framework import status
from common.util import compress_image


@login_required
def internal_groups_detail(request, internal_group_id):
    if request.method == "GET":
        try:
            internal_group = InternalGroup.objects.get(pk=internal_group_id)
        except InternalGroup.DoesNotExist:
            return render(request, template_name="internal/not_found.html")

        all_internal_groups = InternalGroup.objects.filter(
            type=InternalGroup.Type.INTERNAL_GROUP
        ).order_by("name")
        all_interest_groups = InternalGroup.objects.filter(
            type=InternalGroup.Type.INTEREST_GROUP
        ).order_by("name")
        ctx = {  # The context returns a list structure of groups the template can loop over to display in the sidebar
            "group_overview": [
                {
                    "title": InternalGroup.Type.INTERNAL_GROUP.label,
                    "groups": all_internal_groups,
                },
                {
                    "title": InternalGroup.Type.INTEREST_GROUP.label,
                    "groups": all_interest_groups,
                },
            ],
            "internal_group": internal_group,
        }
        return render(
            request,
            template_name="organization/internal_groups_detail.html",
            context=ctx,
        )
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)


@login_required
def internal_groups_edit(request, internal_group_id):
    internal_group = get_object_or_404(InternalGroup, pk=internal_group_id)
    form = InternalGroupForm(
        request.POST or None, request.FILES or None, instance=internal_group
    )

    ctx = {
        "internal_group": internal_group,
        "internal_group_form": form,
    }
    if request.method == "GET":
        return render(
            request, template_name="organization/internal_groups_edit.html", context=ctx
        )

    elif request.method == "POST":
        if form.is_valid():
            pre_commit_form = form.save(commit=False)
            pre_commit_form.group_image = compress_image(
                pre_commit_form.group_image.file, 1200, 900, 80
            )
            pre_commit_form.save()
            return redirect(
                reverse(
                    internal_groups_detail,
                    kwargs={"internal_group_id": internal_group_id},
                )
            )
        return render(
            request,
            template_name="organization/internal_groups_detail.html",
            context={},
        )
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)
