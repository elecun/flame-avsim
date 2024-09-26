from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.shortcuts import redirect


# 2-back task index page
def index_2back(request):
    return render(request, "html/index_2back.html")

def card_2back(request):
    return render(request, "html/card_2back.html")

