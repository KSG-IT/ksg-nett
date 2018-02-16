from django.shortcuts import render

from summaries.models import Summary


def summaries_list(request):
    ctx = {
        'summaries': Summary.objects.all()
    }
    return render(request, template_name='summaries/summaries_list.html', context=ctx)

