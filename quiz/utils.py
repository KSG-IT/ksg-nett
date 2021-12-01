
from django.db.models.fields import SlugField
from django.shortcuts import get_object_or_404
from organization.models import InternalGroup
from users.models import User


def user_quiz_pool_helper(quiz, internal_group):
    pool = None
    group = None
    if internal_group == "new-members":
        all_groups = InternalGroup.objects.filter(
            type=InternalGroup.Type.INTERNAL_GROUP
        ).order_by("?")
    else:
        all_groups = InternalGroup.objects.filter(slug=internal_group).order_by("?")
    pool = []
    for group in all_groups:
        pool.extend([membership.user for membership in group.active_members])
    return pool

    pool_setup = user_quiz_pool_helper(quiz, internal_group)
    quiz.fake_users.set(pool_setup)

def guess_helper(quiz, user_id):
    participant = quiz.current_guess
    participant.guessed_user = User.objects.get(pk=user_id)
    participant.save()


