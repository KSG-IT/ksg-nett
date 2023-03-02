from django.conf import settings
from django.core.files.temp import NamedTemporaryFile
from django.template.loader import render_to_string
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from common.util import send_email
from economy.models import SociProduct
from economy.schema import BankAccountActivity


def parse_deposit(deposit):
    return BankAccountActivity(
        name="Innskudd",
        amount=deposit.amount,
        timestamp=deposit.approved_at,
        quantity=None,
    )


def stilletime_closed_email_notification(soci_session):
    pass


def parse_transfer(transfer, user):
    # The sign of the amount depends on if the user is the source or destination of the transfer
    if transfer.destination == user.bank_account:
        sign = 1
    else:
        sign = -1

    return BankAccountActivity(
        name="Overføring",
        amount=transfer.amount * sign,
        timestamp=transfer.created_at,
        quantity=None,
    )


def parse_product_order(product_order):
    quantity = product_order.order_size
    if product_order.product.sku_number == settings.DIRECT_CHARGE_SKU:
        quantity = 1

    return BankAccountActivity(
        name=product_order.product.name,
        amount=product_order.cost,
        timestamp=product_order.purchased_at,
        quantity=quantity,
    )


def parse_transaction_history(bank_account, slice=None):
    """
    Accepts a SociBankAccount object and parses its transaction history
    to the generic format of a BankAccountActivity. Optional keywordargument
    slice determines how many such objects we want
    """
    transaction_history = bank_account.transaction_history
    user = bank_account.user

    parsed_transfers = [
        parse_transfer(transfer, user) for transfer in transaction_history["transfers"]
    ]
    parsed_product_orders = [
        parse_product_order(product_order)
        for product_order in transaction_history["product_orders"].prefetch_related(
            "product"
        )
    ]
    parsed_deposits = [
        parse_deposit(deposit)
        for deposit in transaction_history["deposits"].filter(approved=True)
    ]

    activities = [*parsed_transfers, *parsed_product_orders, *parsed_deposits]
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    if slice:
        activities = activities[:slice]

    return activities


def send_soci_order_session_invitation_email(soci_session, invited_users):
    email_list = invited_users.values_list("email", flat=True)

    content = f"""
        Hei!

        Du er herved invitert på stilletime. Logg inn på KSG-nett for å legge inn matbestilling.
        """

    html_content = f"""
                Hei! 
                <br>
                <br>
                Du er herved invitert på stilletime. Logg inn på KSG-nett for å legge inn matbestilling.
            """

    send_email(
        recipients=email_list,
        subject="Invitasjon til Sosialt Selskap",
        message=content,
        html_message=html_content,
    )


def create_food_order_pdf_file(order_session):
    orders = order_session.orders.filter(product__type=SociProduct.Type.FOOD)

    summary = []
    for product in orders.values("product").distinct():
        product_obj = SociProduct.objects.get(pk=product["product"])
        order_count = orders.filter(product=product_obj).count()
        summary.append(
            {
                "name": product_obj.name,
                "count": order_count,
            }
        )

    context = {
        "orders": orders,
        "summary": summary,
    }
    html_content = render_to_string(
        template_name="economy/food_orders.html", context=context
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


def send_deposit_approved_email(deposit):
    email_list = [deposit.account.user.email]

    content = f"""
        Hei!

        Ditt innskudd på {deposit.amount} kr er nå godkjent. Du kan nå bruke pengene på KSG-nett.
        
        Du får {deposit.resolved_amount} kr på konto.
        """

    html_content = f"""
                Hei! 
                <br>
                <br>
                Ditt innskudd på {deposit.amount} kr er nå godkjent. Du kan nå bruke pengene på KSG-nett.
                <br>
                Du får {deposit.resolved_amount} kr på konto.
            """

    send_email(
        recipients=email_list,
        subject="Innskudd godkjent",
        message=content,
        html_message=html_content,
    )


def send_deposit_refunded_email(deposit):
    email_list = [deposit.account.user.email]

    content = f"""
        Hei!
        
        Ditt innskudd på {deposit.amount} kr er nå refundert. Det kan ta litt tid før pengene er tilbake
        på kontoen din. Du har blitt trukket for {deposit.resolved_amount} kr på KSG-nett.
        
        Du får {deposit.resolved_amount} kr på konto.
        """

    html_content = f"""
                Hei!
                <br>
                <br>
                Ditt innskudd på {deposit.amount} kr er nå refundert. Det kan ta litt tid før pengene er tilbake 
                på kontoen din. Du har blitt trukket for {deposit.resolved_amount} kr på KSG-nett.
            """

    send_email(
        recipients=email_list,
        subject="Innskudd refundert",
        message=content,
        html_message=html_content,
    )


def stripe_create_Payment_intent(amount, customer=None, charge_saved_card=False):
    import stripe
    import math

    amount_in_smallest_currency = amount * 100
    STRIPE_API_KEY = settings.STRIPE_SECRET_KEY

    if not STRIPE_API_KEY:
        raise EnvironmentError("Stripe API key missing")

    STRIPE_FLAT_FEE = settings.STRIPE_FLAT_FEE * 100
    STRIPE_PERCENTAGE_FEE = settings.STRIPE_PERCENTAGE_FEE / 100.0

    percentage_applied = amount_in_smallest_currency * STRIPE_PERCENTAGE_FEE
    total_fee_in_smallest_currency = percentage_applied + STRIPE_FLAT_FEE

    resolved_amount_in_smallest_currency = math.floor(
        amount_in_smallest_currency - total_fee_in_smallest_currency
    )
    resolved_amount_in_nok = math.floor(resolved_amount_in_smallest_currency / 100.0)

    stripe.api_key = STRIPE_API_KEY

    if customer:
        customer_id = stripe_search_customer(f"email:'{customer.email}'")

        if not customer_id:
            customer_id = create_new_stripe_customer(customer)

        if charge_saved_card:
            try:
                data = stripe.PaymentMethod.list(customer=customer_id, type="card")
                default_payment_method = data["data"][0]["id"]
            except IndexError:
                default_payment_method = None
        else:
            default_payment_method = None

        intent = stripe.PaymentIntent.create(
            amount=amount_in_smallest_currency,
            currency="nok",
            automatic_payment_methods={"enabled": True},
            customer=customer_id,
            # payment_method=default_payment_method,
            # off_session=bool(default_payment_method),
            # confirm=bool(default_payment_method),
            # return_url=settings.APP_URL + "/economy/me",
            payment_method_options={
                "card": {
                    # Stripe recommends automatic but since European regulations require
                    # 3D Secure for all transactions, we use any.
                    "request_three_d_secure": "any",
                }
            },
        )
    else:
        intent = stripe.PaymentIntent.create(
            amount=amount_in_smallest_currency,
            currency="nok",
            automatic_payment_methods={"enabled": True},
        )
    return intent, resolved_amount_in_nok


def stripe_search_customer(query_string):
    import stripe

    res = stripe.Customer.search(query=query_string)
    data = res["data"]

    if len(data) == 0:
        return None

    if len(data) > 1:
        raise Exception(
            f"Multiple Stripe customers resolved for query string: {query_string}"
        )

    customer_data = data[0]
    return customer_data["id"]


def create_new_stripe_customer(customer):
    import stripe

    customer = stripe.Customer.create(
        name=customer.get_full_name(), email=customer.email, phone=customer.phone
    )
    return customer.id
