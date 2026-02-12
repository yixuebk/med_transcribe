"""Transcriber App URL Config"""
from django.urls import path

from . import views


app_name = 'transcriber'

urlpatterns = [
    # HttpResponse
    path('', views.recorder, name='recorder'),
    path('result/<str:query_id>', views.result, name='result'),
    path('results', views.result_list, name='result_list'),
    path('delete/<str:query_id>', views.delete_result, name='delete_result'),
    path('delete', views.delete_result_multi, name='delete_result_multi'),

    # JsonResponse
    path('api/transcribe', views.api_transcribe, name='api_transcribe'),
    path('api/basic_transcribe', views.api_basic_transcribe, name='api_basic_transcribe'),
    path('api/audio/<str:query_id>', views.api_audio, name='api_audio'),
    path('api/update/soap/', views.api_update_soap, name='api_update_soap'),
]
