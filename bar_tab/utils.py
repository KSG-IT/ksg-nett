from common.util import send_email
from django.db.models import Sum
from bar_tab.models import BarTab, BarTabOrder
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration


def normalize_customer_orders(orders):
    from .schema import CustomerBarTabSummaryItem

    summary_dict = {}
    for order in orders:
        dict_key = order.get_name_display
        existing_total = summary_dict.get(dict_key, 0)
        summary_dict[dict_key] = existing_total + order.cost

    parsed_orders = []
    for key, value in summary_dict.items():
        parsed_orders.append(
            CustomerBarTabSummaryItem(identifying_name=key, total=value)
        )
    return parsed_orders


def normalize_customer_bar_tab_data(bar_tab: BarTab, customers):
    from .schema import BarTabCustomerData

    data = []
    for customer in customers:
        orders = customer.orders.filter(bar_tab=bar_tab).order_by("name")
        away_orders = orders.filter(away=True)
        home_orders = orders.filter(away=False)
        normalized_orders = normalize_customer_orders(home_orders)

        we_owe = away_orders.aggregate(Sum("cost"))["cost__sum"] or 0
        total_cost = sum([customer_tab.total for customer_tab in normalized_orders])
        debt = total_cost - we_owe

        data.append(
            BarTabCustomerData(
                customer=customer,
                bar_tab=bar_tab,
                orders=orders,
                summary_data=normalized_orders,
                total=total_cost,
                we_owe=we_owe,
                debt=debt,
            )
        )

    return data


def create_invoices_from_bar_tab_data(data, user=None):
    from .models import BarTabInvoice

    for customer_data in data:
        BarTabInvoice.objects.create(
            customer=customer_data.customer,
            we_owe=customer_data.we_owe,
            they_owe=customer_data.total,
            amount=customer_data.debt,
            bar_tab=customer_data.bar_tab,
            created_by=user,
        )


def create_pdfs_from_invoices(invoices):
    for invoice in invoices:
        file = create_pdf_file(invoice)
        invoice.pdf.save(
            f"BSF Faktura KSG {invoice.id} - {invoice.customer.name} .pdf", file
        )


def create_pdf_file(invoice):
    orders = invoice.bar_tab.orders.filter(customer=invoice.customer)
    away, home = orders.filter(away=True), orders.filter(away=False)

    bong_away = away.filter(type=BarTabOrder.Type.BONG)
    bong_home = home.filter(type=BarTabOrder.Type.BONG)
    list_away = away.filter(type=BarTabOrder.Type.LIST)
    list_home = home.filter(type=BarTabOrder.Type.LIST)

    away_orders_summarized_by_name = {}
    for order in list_away:
        cost = away_orders_summarized_by_name.get(order.name, None)

        if cost:
            away_orders_summarized_by_name[order.name] += order.cost
        else:
            away_orders_summarized_by_name.update({order.name: order.cost})

    for order in bong_away:
        cost = away_orders_summarized_by_name.get(order.name, None)

        if cost:
            away_orders_summarized_by_name[BarTabOrder.Type.BONG] += order.cost
        else:
            away_orders_summarized_by_name.update({BarTabOrder.Type.BONG: order.cost})

    home_orders_summarized_by_name = {}
    for order in list_home:
        cost = home_orders_summarized_by_name.get(order.name, None)
        if cost:
            home_orders_summarized_by_name[order.name] += order.cost
        else:
            home_orders_summarized_by_name.update({order.name: order.cost})

    for order in bong_home:
        cost = home_orders_summarized_by_name.get(order.name, None)
        if cost:
            home_orders_summarized_by_name[BarTabOrder.Type.BONG] += order.cost
        else:
            home_orders_summarized_by_name.update({BarTabOrder.Type.BONG: order.cost})

    context = {
        "invoice": invoice,
        "away_orders": away,
        "away_sum": sum([order.cost for order in away]),
        "home_orders": home,
        "away_orders_summarized_by_name": away_orders_summarized_by_name,
        "home_orders_summarized_by_name": home_orders_summarized_by_name,
        "home_sum": sum([order.cost for order in home]),
    }

    html_content = render_to_string(
        template_name="bar_tab/invoice.html", context=context
    )

    font_config = FontConfiguration()
    css = CSS(
        string="""
        @import url('https://fonts.googleapis.com/css?family=Work+Sans:300,400,600,700&display=swap');
    """,
        font_config=font_config,
    )

    file = NamedTemporaryFile(delete=True)
    HTML(string=html_content, base_url=settings.BASE_URL).write_pdf(
        file, stylesheets=[css], font_config=font_config
    )
    return file


def send_invoice_email(invoice, user):
    content = """
            Hei!

            Vedlagt finner du faktura fra BSF
            
            Med vennlig hilsen
            KSG
        """

    html_content = """
                Hei!
                <br />
                <br />
                Vedlagt finner du faktura fra BSF
                <br />
                <br />
                Med vennlig hilsen
                <br />
                KSG
     """

    return send_email(
        f"BSF Faktura #{invoice.id} - {invoice.customer.name}",
        message=content,
        reply_to="ksg-soci-okonomi@samfundet.no og",
        fail_silently=False,
        html_message=html_content,
        recipients=[invoice.customer.email],
        cc=[user.email],
        attachments=[invoice.pdf],
    )
