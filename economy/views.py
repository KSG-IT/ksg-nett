from django.shortcuts import render
from economy.forms import DepositForm, DepositCommentForm
from economy.models import Deposit, DepositComment, SociBankAccount
from django.shortcuts import render, get_object_or_404, redirect, HttpResponse
from django.urls import reverse
import datetime


def economy_home(request):
    if request.method == "GET":
        ctx = {
            'deposit_form': DepositForm(),
            'deposit_history': Deposit.objects.filter(account=request.user.bank_account),
            'current_user': request.user
        }
        return render(request, template_name='economy/economy_home.html', context=ctx)

    elif request.method == "POST":  # Should this maybe be handled in a different view?
        form = DepositForm(request.POST, request.FILES)
        if form.is_valid(): # needs handling for when form.is_valid() is False
            obj = form.save(commit=False)
            obj.account = request.user.bank_account
            obj.save()

            ctx = {
                'deposit_form': DepositForm(),
                'deposit_history': Deposit.objects.filter(account=request.user.bank_account),
                'current_user': request.user
            }
            return render(request, template_name='economy/economy_home.html', context=ctx)


def deposits(request):
    if request.method == "GET":
        ctx = {
            'deposits_not_approved': Deposit.objects.filter(signed_off_by=None),
            'deposits_approved': Deposit.objects.exclude(signed_off_by=None)
        }
        return render(request, template_name='economy/economy_deposits.html', context=ctx)


def deposit_approve(request, deposit_id):
    if request.method == "POST":
        deposit = get_object_or_404(Deposit, pk=deposit_id)
        soci_account = get_object_or_404(SociBankAccount, pk=deposit.account.id)
        soci_account.add_funds(deposit.amount)
        deposit.signed_off_by = request.user
        deposit.signed_off_time = datetime.datetime.now()
        deposit.save()
        return redirect(reverse(deposits))


def deposit_invalidate(request, deposit_id):
    if request.method == "POST":
        deposit = get_object_or_404(Deposit, pk=deposit_id)
        soci_account = get_object_or_404(SociBankAccount, pk=deposit.account.id)
        soci_account.remove_funds(deposit.amount)
        deposit.signed_off_by = None
        deposit.signed_off_time = None
        deposit.save()
        return redirect(reverse(deposits))


# TODO: Refactor so it looks cleaner
def deposit_detail(request, deposit_id):
    """Is a lot the code here redundant? Can the logic be simplified somewhat?"""
    if request.method == "GET":
        deposit = get_object_or_404(Deposit, pk=deposit_id)
        deposit_comment = DepositComment.objects.filter(deposit=deposit)
        ctx = {
            'deposit': deposit,
            'deposit_comment': deposit_comment,
            'comment_form': DepositCommentForm()
        }
        return render(request, template_name='economy/economy_deposit_detail.html', context=ctx)

    elif request.method == "POST":
        deposit = get_object_or_404(Deposit, pk=deposit_id)
        deposit_comment = DepositCommentForm(request.POST)
        if deposit_comment.is_valid():
            obj = deposit_comment.save(commit=False)
            obj.deposit = deposit
            obj.user = request.user
            obj.save()

            deposit = get_object_or_404(Deposit, pk=deposit_id)  # wtf am i doing here
            deposit_comment = DepositComment.objects.filter(deposit=deposit).order_by('created_at')
            ctx = {
                'deposit': deposit,
                'deposit_comment': deposit_comment,
                'comment_form': DepositCommentForm()
            }
            return render(request, template_name='economy/economy_deposit_detail.html', context=ctx)
