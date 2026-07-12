from django.urls import path

from apps.pdi import views

app_name = 'pdi'

urlpatterns = [
    path('', views.PDIListView.as_view(), name='list'),
    path('new/', views.PDICreateView.as_view(), name='create'),
    path('<int:pk>/', views.PDIDetailView.as_view(), name='detail'),
]
