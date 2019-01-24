from django.urls import path, include

from api.views import SociProductListView, SociBankAccountBalanceDetailView, SociBankAccountChargeView

urlpatterns = [
    path('economy/', include([
        path('products', SociProductListView.as_view(), name='products'),
        path('bank-accounts/', include([
            path('balance', SociBankAccountBalanceDetailView.as_view(), name='balance'),
            path('<int:id>/charge', SociBankAccountChargeView.as_view(), name='charge'),
        ])),
    ])),
]
