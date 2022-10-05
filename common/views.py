from django.http import HttpRequest, HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML


def print_pdf_example(request: HttpRequest):
    html_content = render_to_string(
        template_name="common/pdf_render_test.html",
        context={"variable": "cool variable!"},
    )

    pdf = HTML(string=html_content).write_pdf()

    response = HttpResponse(content_type="application/pdf;")
    response["Content-Disposition"] = "inline; filename=list_people.pdf"
    response["Content-Transfer-Encoding"] = "binary"

    response.write(pdf)

    return response
