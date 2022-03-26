from io import StringIO

from django.core.management import call_command
from django.test import TestCase


class GenerateActiveAdmission(TestCase):
    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "generate_active_admission",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test__dry_run__generates_admission(self):
        self.call_command()
