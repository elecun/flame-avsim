from django.urls import path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from app_nback_auditory import views


urlpatterns = [
    path('', views.index, name="app_nback_auditory_index"),
]
urlpatterns += staticfiles_urlpatterns()