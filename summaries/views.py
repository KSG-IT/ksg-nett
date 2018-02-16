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

