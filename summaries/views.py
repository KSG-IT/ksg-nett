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

def summaries_ype(request: HttpRequest):
    return redirect(reverse(summaries_list))

def summaries_last(request: HttpRequest):
    return redirect(reverse(summaries_list))


def summaries_search(request: HttpRequest):
    return redirect(reverse(summaries_list))


def summaries_archive(request: HttpRequest):
    return redirect(reverse(summaries_list))
