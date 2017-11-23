from django.shortcuts import render
from rest_framework import viewsets

from quotes.models import Quote, QuoteVote
from quotes.serializers import QuoteSerializer, QuoteVoteSerializer


def list_view(request):
    ctx = {
        'pending': Quote.pending_objects.all(),
        'quotes': Quote.verified_objects.all()
    }
    return render(request, template_name='quotes/quotes_list.html', context=ctx)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer


class QuoteVoteViewSet(viewsets.ModelViewSet):
    queryset = QuoteVote.objects.all()
    serializer_class = QuoteVoteSerializer
