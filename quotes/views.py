from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets

from quotes.models import Quote, QuoteVote
from quotes.serializers import QuoteSerializer, QuoteVoteSerializer


def list_view(request):
    ctx = {
        'pending': Quote.pending_objects.all(),
        'quotes': Quote.verified_objects.all()
    }
    return render(request, template_name='quotes/quotes_list.html', context=ctx)


def vote_up(request, quote_id):
    if request.method == "POST":
        quote = get_object_or_404(Quote.verified_objects, pk=quote_id)
        user = request.user
        quote_vote = QuoteVote.objects.filter(
            quote=quote,
            caster=user
        ).first()

        # If the user already has cast a vote
        if quote_vote is not None:
            # And the vote is already positive
            if quote_vote.value > 0:
                return HttpResponse(200)
            # If the vote was down, change it
            else:
                quote_vote.value = 1
                quote_vote.save()
                return HttpResponse(200)
        else:
            QuoteVote(
                quote=quote,
                caster=user,
                value=1
            ).save()
            return HttpResponse(200)
    else:
        return HttpResponse(status=405)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer


class QuoteVoteViewSet(viewsets.ModelViewSet):
    queryset = QuoteVote.objects.all()
    serializer_class = QuoteVoteSerializer
