from django.conf.urls import url

from api.views import SociProductsView
from .decorators import decorated_balance_view, decorated_charge_view

urlpatterns = [
    url(r'^economy/products/', SociProductsView.as_view(), name='products'),
    url(r'^economy/balance/', decorated_balance_view, name='check-balance'),
    url(r'^economy/charge/', decorated_charge_view, name='charge'),
]
