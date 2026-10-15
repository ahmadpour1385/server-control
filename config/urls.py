from django.urls import path, include
from config import auth_views

urlpatterns = [
    path('login/', auth_views.login_view, name='login'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('monitor/', include('apps.monitor.urls')),
    path('terminal/', include('apps.terminal.urls')),
    path('files/', include('apps.files.urls')),
    path('projects/', include('apps.projects.urls')),
    path('dns/', include('apps.dns.urls')),
    path('', include('apps.servers.urls')),
]