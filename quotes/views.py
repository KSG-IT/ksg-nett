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
        return redirect(reverse(quotes_list))


@login_required
def quotes_archive_overview(request):
    semesters = get_semester_year_shorthands_by_count(15)
    ctx = {
        'semesters': semesters
    }
    return render(request, template_name='quotes/quotes_archive_overview.html', context=ctx)


"""
As of now this method works by extracting the time of year in terms of spring or autumn from the input
which comes at the format like V18 or H17. The view then generates a datetime object in an interval such that
our function which gives a shorthand format can be used to match any quotes which fall within the 
same specified semester. This is a rough draft on hwo to exctracted and should be refactored at some point.
At the point of time I'm writing this the view neither has sufficient form for error handling which 
has to be implemented before committing anything to develop.

The view also renders pending objects as of now which it shouldn't. 
"""

# Deprecated until further notice
# @login_required
# def quotes_archive_specific(request, quote_semester):
#     # Need to create timezone object, could extract the prefix and generate a datetime object from that
#     # Error handling for wrong format, either too long or not valid semester
#     semester_prefix = quote_semester[0]
#     year = int('20' + quote_semester[1:3])
#     semester_datetime_object = timezone.now()
#     if semester_prefix == 'H':
#         semester_datetime_object = semester_datetime_object.replace(year=year, month=10, day=4)
#     elif semester_prefix == 'V':
#         semester_datetime_object = semester_datetime_object.replace(year=year, month=3, day=4)
#
#     ctx = {
#         'semester_specific': get_semester_year_shorthand(semester_datetime_object),
#         'semester_quotes': Quote.objects.in_semester(semester_datetime_object).order_by('-created')
#     }
#     return render(request, template_name='quotes/quotes_archive_specific.html', context=ctx)


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
