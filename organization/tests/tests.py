# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from organization.tests.factories import InternalGroupFactory
from users.tests.factories import UserFactory


class GroupTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.group_1 = InternalGroupFactory()
        cls.user_1 = UserFactory()
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
