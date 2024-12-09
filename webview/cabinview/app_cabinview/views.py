from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.shortcuts import redirect


def index(request):
    return render(request, "index.html")

def button_event(request):
    return render(request, "button_event.html")

def wifi_qr(request):
    return render(request, "wifi_qr.html")