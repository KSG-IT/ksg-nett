from django.shortcuts import render, get_object_or_404

from summaries.models import Summary


def summaries_list(request):
    ctx = {
        'summaries': Summary.objects.all()
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

