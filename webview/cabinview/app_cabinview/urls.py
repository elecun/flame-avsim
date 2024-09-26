from django.urls import path
from app_cabinview import views


urlpatterns = [
    path('', views.index, name="cabinview_index"),
]