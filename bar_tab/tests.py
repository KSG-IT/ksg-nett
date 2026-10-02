from django.test import TestCase

from bar_tab.models import (
    BarTab,
    BarTabCustomer,
    BarTabInvoice,
    BarTabOrder,
    BarTabProduct,
)
from bar_tab.utils import INVOICE_LOGO_PATH, create_pdf_file
from users.tests.factories import UserFactory


class TestCreatePdfFile(TestCase):
    def setUp(self) -> None:
        user = UserFactory.create()
        self.customer = BarTabCustomer.objects.create(
            name="Lyche", short_name="LY", email="lyche@example.com"
        )
        bar_tab = BarTab.objects.create(created_by=user)
        product = BarTabProduct.objects.create(name="Øl", price=50)

        for away, type, name in [
            (False, BarTabOrder.Type.BONG, ""),
            (False, BarTabOrder.Type.LIST, "Ola Nordmann"),
            (False, BarTabOrder.Type.LIST, "Ola Nordmann"),
            (True, BarTabOrder.Type.LIST, "Kari Nordmann"),
        ]:
            BarTabOrder.objects.create(
                bar_tab=bar_tab,
                customer=self.customer,
                product=product,
                type=type,
                name=name,
                away=away,
                quantity=2,
                cost=100,
            )

        self.invoice = BarTabInvoice.objects.create(
            bar_tab=bar_tab,
            customer=self.customer,
            created_by=user,
            we_owe=100,
            they_owe=300,
            amount=200,
        )

    def test__create_pdf_file__returns_pdf(self):
        file = create_pdf_file(self.invoice)
        file.seek(0)
        content = file.read()

        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertIn(b"%%EOF", content[-1024:])

    def test__create_pdf_file_without_orders__returns_pdf(self):
        self.invoice.bar_tab.orders.all().delete()

        file = create_pdf_file(self.invoice)
        file.seek(0)

        self.assertTrue(file.read().startswith(b"%PDF-"))

    def test__invoice_logo__exists(self):
        self.assertTrue(INVOICE_LOGO_PATH.is_file())
