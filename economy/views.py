from django.shortcuts import render
from economy.forms import DepositForm
from economy.models import Deposit
from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.urls import reverse


# Create your views here.


def deposit(request):
    if request.method == "GET":
        ctx = {
            'deposit_form': DepositForm(),
            'deposit_history': Deposit.objects.filter(account=request.user.bank_account)
        }
        return render(request, template_name='economy/deposit.html', context=ctx)
    elif request.method == "POST":

        form = DepositForm(request.POST)
        if form.is_valid():
            form.save(commit=False)
            form.account = request.user.bank_account
            form.save()
            return HttpResponse('Success')

        ctx = {
            'deposit_form': DepositForm(),
            'deposit_history': Deposit.objects.filter(account=request.user.bank_account)
        }
        return render(request, template_name='economy/deposit.html', context=ctx)


