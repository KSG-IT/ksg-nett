from django.urls import path, include

from api.views import SociProductsView
from .decorators import decorated_balance_view, decorated_charge_view

urlpatterns = [
    path('economy/', include([
        path('products/', SociProductsView.as_view(), name='products'),
        path('balance/', decorated_balance_view, name='check-balance'),
        path('charge/', decorated_charge_view, name='charge'),
    ])),
]
