from django.urls import path, re_path
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from app_nback_visual import views


urlpatterns = [
    path('', views.index_nback, name="app_nback_visual_index"),
    # 2-back task
    path('2/', views.index_2back, name="app_nback_visual_view"),
]

urlpatterns += staticfiles_urlpatterns()