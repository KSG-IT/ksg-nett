# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from organization.tests.factories import InternalGroupFactory
from users.tests.factories import UserFactory
from organization.models import InternalGroup


# TODO rewrite group tests after deciding on model structures

class TestInternalGroup(TestCase):
    def setUp(self) -> None:
        self.internal_group = InternalGroupFactory.create(name="Lyche bar")

    def test__internal_group_slug__returns_correct_string_format(self):
        print(self.internal_group.get_group_slug)
        pass