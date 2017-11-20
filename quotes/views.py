from rest_framework import viewsets

from quotes.models import Quote, QuoteVote
from quotes.serializers import QuoteSerializer, QuoteVoteSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer


class QuoteVoteViewSet(viewsets.ModelViewSet):
    queryset = QuoteVote.objects.all()
    serializer_class = QuoteVoteSerializer
