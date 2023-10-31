import math

from django.db.models.functions import Coalesce
from django.db.models import Sum
from django.utils import timezone
from economy.models import ProductOrder, SociProduct, ProductGhostOrder
from django.conf import settings


def calculate_stock_price_for_product(product_id: int, fail_silently=True):
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

    purchase_window = timezone.now() - settings.STOCK_MODE_PRICE_WINDOW
    purchases_made_in_window = ProductOrder.objects.filter(
        product_id=product_id, purchased_at__gte=purchase_window
    )

    purchase_volume = purchases_made_in_window.aggregate(
        volume=Coalesce(Sum("order_size"), 0)
    )["volume"]

    ghost_volume = ProductGhostOrder.objects.filter(
        product=product, timestamp__gte=purchase_window
    ).count()

    total_sales_volume = ghost_volume + purchase_volume

    popularity_tax = total_sales_volume * settings.STOCK_MODE_PRICE_MULTIPLIER
    product = SociProduct.objects.get(id=product_id)

    calculated_price = math.floor(product.purchase_price + popularity_tax)
    return calculated_price
