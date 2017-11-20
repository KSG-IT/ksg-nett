from django.shortcuts import render
from quotes.models import Quote
from quotes.serializers import QuoteSerializer



class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer
