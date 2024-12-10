from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.shortcuts import redirect


def index_nback(request):
    return render(request, "html/nback.html")

def index_nback_qr(request):
    return render(request, "html/nback_link_qr.html")

def index_nback_phone(request):
    return render(request, "html/nback_phone.html")
