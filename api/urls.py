from django.urls import path, include

from api.views import CustomTokenObtainSlidingView, CustomTokenRefreshSlidingView, CustomTokenVerifyView, \
    SociProductListView, SociBankAccountBalanceDetailView, SociBankAccountChargeView, TerminateSociSessionView, \
    SensorMeasurementView

urlpatterns = [
    path('authentication/', include([
        path('obtain-token', CustomTokenObtainSlidingView.as_view(), name='obtain-token'),
        path('refresh-token', CustomTokenRefreshSlidingView.as_view(), name='refresh-token'),
        path('verify-token', CustomTokenVerifyView.as_view(), name='verify-token'),
    ])),
    path('economy/', include([
        path('products', SociProductListView.as_view(), name='products'),
        path('bank-accounts/', include([
            path('balance', SociBankAccountBalanceDetailView.as_view(), name='balance'),
            path('<int:id>/charge', SociBankAccountChargeView.as_view(), name='charge'),
        ])),
        path('sessions/terminate', TerminateSociSessionView.as_view(), name='terminate-session'),
    ])),
    path('sensors/', include([
        path('measurements/', SensorMeasurementView.as_view(), name='measurements')
    ]))
]
