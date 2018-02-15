from django.shortcuts import render


def index(request):
    """
    External index page, i.e. the landing page of ksg-nett.

    :param request:
    :return:
    """
    return render(request, 'external/base.html')
