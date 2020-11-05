from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from weasyprint import HTML

from internal.views import index as internal_index
from login.views import login_user


def index(request):
    """
    This view is the root index of the application. It is responsible for
    routing the requestor to the right place.

    :param request:
    :return:
    """
    if request.user.is_authenticated:
        return redirect(reverse(internal_index))
    else:
        return redirect(reverse(login_user))


def print_pdf_example(request: HttpRequest):
    html_content = render_to_string(
        template_name="common/pdf_render_test.html" ,
        context={
            "variable": "cool variable!"
        }
    )

    pdf = HTML(string=html_content).write_pdf()

    response = HttpResponse(content_type='application/pdf;')
    response['Content-Disposition'] = 'inline; filename=list_people.pdf'
    response['Content-Transfer-Encoding'] = 'binary'

    response.write(pdf)

    return response

