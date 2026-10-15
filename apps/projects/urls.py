from django.urls import path
from . import views

urlpatterns = [
    path('<str:sid>/', views.page, name='projects'),
    path('<str:sid>/add/', views.add, name='projects_add'),
    path('p/<str:pid>/status/', views.status, name='projects_status'),
    path('p/<str:pid>/delete/', views.delete, name='projects_delete'),
    path('p/<str:pid>/<str:act>/', views.action, name='projects_action'),
]