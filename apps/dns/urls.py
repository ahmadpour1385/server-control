from django.urls import path
from . import views

urlpatterns = [
    path('', views.page, name='dns'),
    path('lookup/', views.lookup, name='dns_lookup'),
    path('check/', views.check, name='dns_check'),
]