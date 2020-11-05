from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from quotes.models import Quote
from summaries.models import Summary
from itertools import chain
from internal.models import SlideshowImage


@login_required
def index(request):
    last_summaries = Summary.objects.order_by('-date')[0:10]
    last_quotes = Quote.verified_objects.all().order_by('-created')[0:10]
    economy_purchases = request.user.bank_account.purchases.all().order_by('-created')[0:10]
    economy_deposits = request.user.verified_deposits.all()[0:10]
    # chains the two lists sorted by date and then we can slice the latest history of the two items
    # not wokring as of now probably need a custom manager to combine the querysets
    result_list = sorted(
        chain(economy_deposits, economy_purchases),
        key=lambda instance: instance.created
    )
    ctx = { 
        'last_summaries': last_summaries,
        'last_quotes': last_quotes,
        'economy:': economy_purchases,
        'next_shifts': request.user.shift_set.filter(slot__group__meet_time__gte=timezone.now())[:2], 
        'slideshow': SlideshowImage.objects.filter(start_datetime__lte=timezone.now()).filter(end_datetime__gte=timezone.now()), 
        
    } 
    return render(request, 'internal/frontpage.html', context=ctx)


@login_required
def not_found(request):
    return render(request, 'internal/not_found.html')
