from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from quotes.models import Quote
from summaries.models import Summary


@login_required
def index(request):
    last_summaries = Summary.objects.order_by('-date')[0:10]
    last_quotes = Quote.verified_objects.all().order_by('-created')[0:10]

    ctx = {
        'last_summaries': last_summaries,
        'last_quotes': last_quotes
    }
    return render(request, 'internal/frontpage.html', context=ctx)


@login_required
def not_found(request):
    return render(request, 'internal/not_found.html')
