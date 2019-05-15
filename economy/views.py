from django.shortcuts import render


# Create your views here.


def deposit_view(request):
    ctx = {

    }
    return render(request, template_name='economy/deposit.html', context=ctx)
