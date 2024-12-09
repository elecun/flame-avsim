from django.urls import path
from app_cabinview import views


urlpatterns = [
    path('', views.index, name="cabinview_index"),
    path('event/', views.button_event, name="cabinview_event"),
    path('wifi/', views.wifi_qr, name="cabinview_wifi_qr"),
]