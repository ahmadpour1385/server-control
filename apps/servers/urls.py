from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('list/', views.server_list, name='server_list'),
    path('add/', views.add, name='add'),
    path('delete/<str:sid>/', views.delete, name='delete'),
    path('resetkey/<str:sid>/', views.reset_key, name='reset_key'),
    path('edit/<str:sid>/', views.edit_form, name='edit_form'),
    path('edit/<str:sid>/save/', views.edit_save, name='edit_save'),
]