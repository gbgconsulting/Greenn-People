from django.urls import path

from apps.talent import views

app_name = 'talent'

urlpatterns = [
    path('matrix/', views.TalentMatrixView.as_view(), name='matrix'),
]
