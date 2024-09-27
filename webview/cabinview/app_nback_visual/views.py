from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.shortcuts import redirect


def index_nback(request):
    return render(request, "html/index.html")

# 2-back task index page
def index_2back(request):
    return render(request, "html/nback.html")

