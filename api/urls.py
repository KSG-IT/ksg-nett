from django.conf.urls import url, include
from rest_framework.routers import DefaultRouter

from api.views import UserViewSet, ListCommissionsView, CreateCommissionView, UpdateCommissionView, DeleteCommissionView
from quotes.views import QuoteViewSet, QuoteVoteViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'quotes', QuoteViewSet)
router.register(r'quote-votes', QuoteVoteViewSet)

urlpatterns = [
    url(r'', include(router.urls)),

    url(r'^commissions/$', ListCommissionsView.as_view(), name='list-commissions'),
    url(r'^commissions/create/', CreateCommissionView.as_view(), name='create-commission'),
    url(r'^commissions/(?P<commission_id>[0-9]+)/update/', UpdateCommissionView.as_view(), name='update-commission'),
    url(r'^commissions/(?P<commission_id>[0-9]+)/delete/', DeleteCommissionView.as_view(), name='delete-commission'),
]
