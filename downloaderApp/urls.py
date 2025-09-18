from django.urls import path
from . import views

urlpatterns = [
    path('', views.download_view, name='download'),
    path('start-download/', views.start_download, name='start_download'),
    path('progress/<str:task_id>/', views.get_progress, name='get_progress'),
    path('download-file/<str:task_id>/', views.download_file, name='download_file'),
]