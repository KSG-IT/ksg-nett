from django.urls import path, include

from api.views import SociProductListView, SociBankAccountBalanceDetailView, ChargeSociBankAccountView

urlpatterns = [
    path('economy/', include([
        path('products/', SociProductListView.as_view(), name='products'),
        path('balance/', SociBankAccountBalanceDetailView.as_view(), name='check-balance'),
        path('charge/', ChargeSociBankAccountView.as_view(), name='charge'),
    ])),
]
