from django.urls import path

from apps.notifications import views

app_name = 'notifications'

urlpatterns = [
    path('logs/', views.NotificacaoLogListView.as_view(), name='log_list'),
]
