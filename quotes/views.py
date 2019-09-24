from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from rest_framework import viewsets, status
from django.utils import timezone
from quotes.forms import QuoteForm
from quotes.models import Quote, QuoteVote
from quotes.serializers import QuoteSerializer, QuoteVoteSerializer
from common.util import get_semester_year_shorthands_by_count, get_semester_year_shorthand


@login_required
def quotes_approve(request, quote_id):
    if request.method == "POST":
        quote = get_object_or_404(Quote, pk=quote_id)
        if quote.verified_by is None:
            quote.verified_by = request.user
            quote.save()
        return redirect(reverse(quotes_pending))
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)



@login_required
def quotes_highscore(request):
    if request.method == "GET":
        this_semester = Quote.highscore_objects.semester_highest_score(timezone.now())
        all_time = Quote.highscore_objects.highest_score_all_time()
        combined_list = list(zip(this_semester, all_time))
        ctx = {
            "highscore_this_semester": Quote.highscore_objects.semester_highest_score(timezone.now()),
            "highscore_all_time": Quote.highscore_objects.highest_score_all_time(),
            "highscore_combined": combined_list # Can be used in the future so we can style the rows together
        }
        return render(request, template_name="quotes/quotes_highscore.html", context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)



@login_required
def quotes_list(request):
    ctx = {
        'pending': Quote.pending_objects.all().order_by('-created'),
        'quotes': Quote.verified_objects.all().order_by('-created'),
        'current_semester': get_semester_year_shorthand(timezone.now())
    }
    return render(request, template_name='quotes/quotes_list.html', context=ctx)


@login_required
def quotes_pending(request):
    ctx = {
        'pending': Quote.pending_objects.all().order_by('-created'),
        'current_semester': get_semester_year_shorthand(timezone.now())
    }
    return render(request, template_name='quotes/quotes_pending.html', context=ctx)


@login_required
def quotes_add(request):
    if request.method == "GET":
        ctx = {
            'quote_form': QuoteForm()
        }
        return render(request, template_name='quotes/quotes_add.html', context=ctx)
    elif request.method == "POST":
        form = QuoteForm(request.POST)
        form.reported_by = request.user
        if form.is_valid():
            form = form.save(commit=False)
            form.reported_by = request.user
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
                return JsonResponse({'sum': quote.sum}, status=status.HTTP_200_OK)
            # If the vote was down, change it
            else:
                quote_vote.value = 1
                quote_vote.save()
                return JsonResponse({'sum': quote.sum}, status=status.HTTP_200_OK)
        else:
            QuoteVote(
                quote=quote,
                caster=user,
                value=1
            ).save()
            return JsonResponse({'sum': quote.sum}, status=status.HTTP_200_OK)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)  # Method not supported


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
                return JsonResponse({'sum': quote.sum}, status=status.HTTP_200_OK)
            # If the vote was up, change it
            else:
                quote_vote.value = -1
                quote_vote.save()
                return JsonResponse({'sum': quote.sum}, status=status.HTTP_200_OK)
        else:
            QuoteVote(
                quote=quote,
                caster=user,
                value=-1
            ).save()
            return JsonResponse({'sum': quote.sum}, status=status.HTTP_200_OK)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)  # Method not supported


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.all()
    serializer_class = QuoteSerializer


class QuoteVoteViewSet(viewsets.ModelViewSet):
    queryset = QuoteVote.objects.all()
    serializer_class = QuoteVoteSerializer
