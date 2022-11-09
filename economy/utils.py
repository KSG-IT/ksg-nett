from django.conf import settings

from economy.schema import BankAccountActivity


def parse_deposit(deposit):
    return BankAccountActivity(
        name="Innskudd",
        amount=deposit.amount,
        timestamp=deposit.signed_off_time,
        quantity=None,
    )


def parse_transfer(transfer, user):
    # The sign of the amount depends of if the user is the source or destination of the transfer
    if transfer.destination == user.bank_account:
        sign = 1
    else:
        sign = -1

    return BankAccountActivity(
        name="Overføring",
        amount=transfer.amount * sign,
        timestamp=transfer.created,
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
    Accepts a SociBankAccount object and and parses its transaction history
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
        for deposit in transaction_history["deposits"].filter(
            signed_off_by__isnull=False
        )
    ]

    activities = [*parsed_transfers, *parsed_product_orders, *parsed_deposits]
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    if slice:
        activities = activities[:slice]

    return activities
