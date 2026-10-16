from django.urls import path
from . import views

urlpatterns = [
    path('<str:sid>/', views.browse, name='files'),
    path('<str:sid>/download/', views.download, name='files_download'),
    path('<str:sid>/upload/', views.upload, name='files_upload'),
    path('<str:sid>/mkdir/', views.mkdir, name='files_mkdir'),
    path('<str:sid>/delete/', views.delete, name='files_delete'),
]