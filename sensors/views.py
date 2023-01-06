from django.http import HttpRequest
from django.shortcuts import render

# Create your views here.
def overview(request: HttpRequest):
    return render(request, 'sensors/overview.html')
