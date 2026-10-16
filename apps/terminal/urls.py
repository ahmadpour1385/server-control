from django.urls import path
from . import views

urlpatterns = [
    path('<str:sid>/', views.page, name='terminal'),
]