from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from rest_framework import viewsets, status

from quotes.forms import QuoteForm
from quotes.models import Quote, QuoteVote
from quotes.serializers import QuoteSerializer, QuoteVoteSerializer


@login_required
def quotes_list(request):
    ctx = {
        'pending': Quote.pending_objects.all(),
        'quotes': Quote.verified_objects.all()
    }
    return render(request, template_name='quotes/quotes_list.html', context=ctx)


@login_required
def quotes_add(request):
    if request.method == "GET":
        ctx = {
            'quote_form': QuoteForm()
        }
        return render(request, template_name='quotes/quotes_add.html', context=ctx)
    elif request.method == "POST":
        form = QuoteForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect(reverse(quotes_list))
        else:
            ctx = {
                'quote_form': form
            }
            return render(request, template_name='quotes/quotes_add.html', context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)  # Method not supported


@login_required
def quotes_edit(request, quote_id):
    quote = get_object_or_404(Quote, pk=quote_id)
    form = QuoteForm(request.POST or None, instance=quote)
    ctx = {
        'quote_form': form,
        'quote': quote
    }
    if request.method == "GET":
        return render(request, template_name='quotes/quotes_edit.html', context=ctx)
    elif request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse(quotes_list))
        else:
            return render(request, template_name='quotes/quotes_edit.html', context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)  # Method not supported


@login_required
def quotes_delete(request, quote_id):
    if request.method != "POST":
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    quote = get_object_or_404(Quote, pk=quote_id)
    quote.delete()

    return redirect(reverse(quotes_list))


@login_required
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
                return HttpResponse(status=status.HTTP_200_OK)
            # If the vote was down, change it
            else:
                quote_vote.value = 1
                quote_vote.save()
                return HttpResponse(status=status.HTTP_200_OK)
        else:
            QuoteVote(
                quote=quote,
                caster=user,
                value=1
            ).save()
            return HttpResponse(status=status.HTTP_200_OK)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)   # Method not supported


@login_required
def vote_down(request, quote_id):
    if request.method == "POST":
        quote = get_object_or_404(Quote.verified_objects, pk=quote_id)
        user = request.user
        quote_vote = QuoteVote.objects.filter(
            quote=quote,
            caster=user
        ).first()

        # If the user already has cast a vote
        if quote_vote is not None:
            # And the vote is already negative
            if quote_vote.value < 0:
                return HttpResponse(status=status.HTTP_200_OK)
            # If the vote was up, change it
            else:
                quote_vote.value = -1
                quote_vote.save()
                return HttpResponse(status=status.HTTP_200_OK)
        else:
            QuoteVote(
                quote=quote,
                caster=user,
                value=-1
            ).save()
            return HttpResponse(status=status.HTTP_200_OK)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)  # Method not supported


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer


class QuoteVoteViewSet(viewsets.ModelViewSet):
    queryset = QuoteVote.objects.all()
    serializer_class = QuoteVoteSerializer
