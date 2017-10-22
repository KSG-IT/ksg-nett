from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import render, redirect
from rest_framework import status


def login_user(request):
    """
    Logs a user in.

    :type request: django.http.HttpRequest
    :return:
    """
    requested_next_url = request.GET.get('next')

    # We are already authenticated.
    if request.user.is_authenticated:
        if requested_next_url:
            return redirect(requested_next_url)
        # TODO: Redirect internal when internal module merges
        return redirect('/')

    if request.method == 'GET':
        return render(request, 'login/login.html')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)
        if user is None:
            return render(request, 'login/login.html', {'errors': 'Bad username or password'})
        else:
            login(request, user)
            if requested_next_url:
                return redirect(requested_next_url, context={'user': user})
            # TODO: Redirect internal when internal module merges
            return redirect('/', context={'user': user})

    return HttpResponse(status=status.HTTP_401_UNAUTHORIZED)


def logout_user(request):
    pass