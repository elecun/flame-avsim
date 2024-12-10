from django.urls import path, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from app_nback_visual import views


urlpatterns = [
    path('', views.index_nback, name="app_nback_visual_index"),
    path('qr/', views.index_nback_qr, name="app_nback_visual_qr"),
    path('phone/', views.index_nback_phone, name="app_nback_visual_phone"),
]

urlpatterns += staticfiles_urlpatterns()