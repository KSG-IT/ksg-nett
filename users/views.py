# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.utils import timezone
import json

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, HttpResponse, redirect
from django.utils.translation import gettext as _
from rest_framework import status
from users.models import User, UsersHaveMadeOut
from django.urls import reverse


@login_required
def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    ctx = {
        # We don't want to name it `user` as it will override the default user attribute
        # (which is the user calling the view).
        "profile_user": user,
        "next_shift": request.user.shift_set.filter(
            slot__group__meet_time__gte=timezone.now()
        ).first(),
    }
    return render(request, template_name="users/profile_page.html", context=ctx)


@login_required
def klinekart(request):
    # OPTIMIZE: This can be optimized slightly by resolving all the values for all entries immediately
    made_out_this_semester = UsersHaveMadeOut.objects.this_semester()
    made_out_this_semester_list = []

    # Regular user ids are never negative, so we assign only negative values to anonymous users,
    # which ensures no collisions.
    anonymous_users_counter = -1

    anonymous_fake_ids = {}

    # We iterate over each association and add a more compact version to the made_out_this_semester_list variable.
    # The format we use is what is required of the klinekart.js app.
    # Each entry looks something like:
    #       [
    #          {id: <user_one_id>, name: <user_one_name>, img: <user_one_img_url>, anonymous: <user_one_is_anonymous>},
    #          {id: <user_two_id>, name: <user_two_name>, img: <user_two_img_url>, anonymous: <user_two_is_anonymous>},
    #       ]
    for association in made_out_this_semester:
        user_one: User = association.user_one
        user_two: User = association.user_two

        # This if-statement, and the one below for user_two, overloads the id of the user in case the user is anonymous.
        # The user is only assigned one fake id, which is cached in the anonymouse_fake_ids dict.
        if user_one.anonymize_in_made_out_map:
            if user_one.id in anonymous_fake_ids:
                user_one_id = anonymous_fake_ids[user_one.id]
            else:
                user_one_id = anonymous_users_counter
                anonymous_fake_ids[user_one.id] = user_one_id
                anonymous_users_counter -= 1
        else:
            user_one_id = user_one.id

        if user_two.anonymize_in_made_out_map:
            if user_two.id in anonymous_fake_ids:
                user_two_id = anonymous_fake_ids[user_two.id]
            else:
                user_two_id = anonymous_users_counter
                anonymous_fake_ids[user_two.id] = user_two_id
                anonymous_users_counter -= 1
        else:
            user_two_id = user_two.id

        made_out_this_semester_list.append(
            [
                {
                    "id": user_one_id,
                    "name": association.user_one.get_full_name()
                    if not association.user_one.anonymize_in_made_out_map
                    else _("Anonymous"),
                    "img": association.user_one.profile_image.url
                    if not association.user_one.anonymize_in_made_out_map
                    else None,
                    "anonymous": association.user_one.anonymize_in_made_out_map,
                },
                {
                    "id": user_two_id,
                    "name": association.user_two.get_full_name()
                    if not association.user_two.anonymize_in_made_out_map
                    else _("Anonymous"),
                    "img": association.user_two.profile_image.url
                    if not association.user_two.anonymize_in_made_out_map
                    else None,
                    "anonymous": association.user_two.anonymize_in_made_out_map,
                },
            ]
        )

    made_out_this_semester_json = json.dumps(made_out_this_semester_list)

    ctx = {"made_out_data": made_out_this_semester_json}

    return render(request, template_name="users/klinekart.html", context=ctx)
