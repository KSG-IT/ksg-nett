import math

from django.db.models.functions import Coalesce
from django.db.models import Sum
from django.utils import timezone
from economy.models import (
    ProductOrder,
    SociProduct,
    ProductGhostOrder,
    StockMarketCrash,
)
from django.conf import settings


def calculate_stock_price_for_product(
    product_id: int, back_in_time_offset=timezone.timedelta(), fail_silently=True
):
    """
    Calculates the price of a product provided a specific product id.
    """
    product = SociProduct.objects.get(id=product_id)

    if not product.purchase_price:
        if fail_silently:
            return product.price
        else:
            raise RuntimeError(
                f"Cannot calculate stock price for product without purchase price: {product}"
            )

    purchase_window_start = timezone.now() - settings.STOCK_MODE_PRICE_WINDOW

    latest_crash = StockMarketCrash.objects.all().order_by("-timestamp").first()
    if latest_crash:
        crash_timestamp = latest_crash.timestamp
    else:
        crash_timestamp = purchase_window_start

    purchase_window_start -= back_in_time_offset
    purchase_window_end = timezone.now() - back_in_time_offset

    purchases_made_in_window = ProductOrder.objects.filter(
        product_id=product_id,
        purchased_at__gte=purchase_window_start,
        purchased_at__lte=purchase_window_end,
    ).filter(
        purchased_at__gte=crash_timestamp,
    )

    purchase_volume = purchases_made_in_window.aggregate(
        volume=Coalesce(Sum("order_size"), 0)
    )["volume"]

    ghost_volume = (
        ProductGhostOrder.objects.filter(
            product=product,
            timestamp__gte=purchase_window_start,
            timestamp__lte=purchase_window_end,
        )
        .filter(
            timestamp__gte=crash_timestamp,
        )
        .count()
    )

    total_sales_volume = ghost_volume + purchase_volume
    popularity_tax = total_sales_volume * settings.STOCK_MODE_PRICE_MULTIPLIER
    product = SociProduct.objects.get(id=product_id)

    calculated_price = math.floor(product.purchase_price + popularity_tax)
    return calculated_price
