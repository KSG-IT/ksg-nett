from django.db.models import Max, Subquery, OuterRef
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, HttpRequest, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework import status

from common.util import get_semester_year_shorthands_by_count, get_semester_year_shorthand, \
    get_semester_date_boundaries_from_shorthand, is_valid_semester_year_shorthand
from summaries.consts import SUMMARY_TYPE_SHORT_NAMES, SUMMARY_TYPE_CHOICES_DICT
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

def summaries_typedetail(request: HttpRequest, type: str):
    semester = request.GET.get('semester')

    # Default to current semester
    if not semester or not is_valid_semester_year_shorthand(semester):
        semester = get_semester_year_shorthand(timezone.now())

    # Return 404 if type is not valid
    if not type in SUMMARY_TYPE_CHOICES_DICT:
        raise Http404()

    semester_start, semester_end = get_semester_date_boundaries_from_shorthand(semester)
    summaries = Summary.objects.filter(
        summary_type=type,
        date__gte=semester_start,
        date__lt=semester_end,
    )\
        .annotate(month=TruncMonth('date'))\
        .order_by('date')

    # The structure we are going for is an array of month objects:
    #  [
    #     {
    #        "month": String,
    #        "summaries": Array
    #     }, ...
    #  ]
    # They will automatically be sorted by month due to the order_by clause above.
    summaries_grouped_by_month = []
    for summary in summaries:
        # Add month translations
        month_name = _(summary.month.strftime("%B"))

        if len(summaries_grouped_by_month) == 0 or summaries_grouped_by_month[-1]['month'] != month_name:
            # Create new month object
            summaries_grouped_by_month.append({
                'month': month_name,
                'summaries': [summary]
            })
        else:
            # Append summary to current month object
            summaries_grouped_by_month[-1]['summaries'].append(summary)

    ctx = {
        'current_type': type,
        'types': SUMMARY_TYPE_SHORT_NAMES,
        'current_semester': semester,
        'semesters': get_semester_year_shorthands_by_count(12),
        'summaries_grouped_by_month': summaries_grouped_by_month,
    }
    return render(request, template_name='summaries/summaries_typedetail.html', context=ctx)


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
    semesters = get_semester_year_shorthands_by_count(16)
    ctx = {
        'semesters': semesters
    }
    return render(request, template_name='summaries/summaries_archive.html', context=ctx)
