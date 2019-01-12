from django.db.models import Max, Subquery, OuterRef
from django.http import HttpResponse, HttpRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from rest_framework import status

from summaries.consts import SUMMARY_TYPE_SHORT_NAMES
from summaries.forms import SummaryForm
from summaries.models import Summary


def summaries_list(request):
    ctx = {
        'summaries': Summary.objects.all(),
        'all_summary_types': SUMMARY_TYPE_SHORT_NAMES
    }
    return render(request, template_name='summaries/summaries_list.html', context=ctx)


def summaries_detail(request, summary_id):
    summary = get_object_or_404(Summary, pk=summary_id)
    ctx = {
        'summary': summary
    }
    return render(request, template_name='summaries/summary_detail.html', context=ctx)


def summaries_create(request):
    form = SummaryForm(request.POST or None)
    ctx = {
        'summary_form': form
    }
    if request.method == "GET":
        return render(request, template_name='summaries/summaries_create.html', context=ctx)
    elif request.method == "POST":
        if form.is_valid():
            instance = form.save()
            return redirect(reverse(summaries_detail, kwargs={'summary_id': instance.id}))
        else:
            return render(request, template_name='summaries/summaries_create.html', context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)


def summaries_update(request, summary_id):
    summary = get_object_or_404(Summary, pk=summary_id)
    form = SummaryForm(request.POST or None, instance=summary)
    ctx = {
        'summary_form': form,
        'summary': summary
    }
    if request.method == "GET":
        return render(request, template_name='summaries/summaries_update.html', context=ctx)
    elif request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect(reverse(summaries_detail, kwargs={'summary_id': summary_id}))
        else:
            return render(request, template_name='summaries/summaries_update.html', context=ctx)
    else:
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)


def summaries_delete(request, summary_id):
    if request.method != "POST":
        return HttpResponse(status=status.HTTP_405_METHOD_NOT_ALLOWED)

    summary = get_object_or_404(Summary, pk=summary_id)
    summary.delete()

    return redirect(reverse(summaries_list))

def summaries_type(request: HttpRequest):
    return redirect(reverse(summaries_list))


def summaries_last(request: HttpRequest):
    # Unfortunately, this is the most pragmatic way to get the latest
    # summary for each type, in a database-independent way, as far as I know.
    latest_summary_dates_subquery = Summary.objects\
        .filter(summary_type=OuterRef('summary_type'))\
        .values('summary_type')\
        .annotate(latest_date=Max('date'))\
        .values('latest_date')[:1]
    last_summaries = Summary.objects.filter(
        date=Subquery(latest_summary_dates_subquery)
    )
    # Convert to list of tuples with display version of summary_type, and date.
    ctx = {
        'last_summaries': last_summaries
    }

    return render(request, template_name='summaries/summaries_last.html', context=ctx)


def summaries_search(request: HttpRequest):
    return redirect(reverse(summaries_list))


def summaries_archive(request: HttpRequest):
    return redirect(reverse(summaries_list))
