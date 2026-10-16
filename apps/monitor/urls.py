from django.urls import path
from . import views

urlpatterns = [
    path('<str:sid>/', views.info, name='monitor_info'),
    path('<str:sid>/connect/', views.connect, name='monitor_connect'),
    path('<str:sid>/forget/', views.forget_saved, name='monitor_forget'),
]