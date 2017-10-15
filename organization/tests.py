# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

# Create your tests here.
from organization.models import Group
from users.models import User


class GroupTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.group_1 = Group(
            name='Group 1'
        )
        cls.group_1.save()

        cls.user_1 = User(
            username='User 1'
        )
        cls.user_1.save()
        cls.group_1.members.add(cls.user_1)

    def test_group_str_and_repr_should_not_fail(self):
        str_representation = str(self.group_1)
        repr_representation = repr(self.group_1)

        self.assertIsInstance(str_representation, str)
        self.assertIsInstance(repr_representation, str)

    def test_group_should_contain_a_user(self):
        self.assertEqual(self.group_1.members.count(), 1)

    def test_group_member_should_have_a_backref(self):
        self.assertEqual(self.user_1.internal_groups.first(), self.group_1)
