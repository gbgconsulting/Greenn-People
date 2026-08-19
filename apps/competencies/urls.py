from django.urls import path

from apps.competencies import views

app_name = 'competencies'

urlpatterns = [
    path('scales/', views.EscalaListView.as_view(), name='escala_list'),
    path('scales/new/', views.EscalaCreateView.as_view(), name='escala_create'),
    path(
        'scales/<int:pk>/edit/',
        views.EscalaUpdateView.as_view(),
        name='escala_update',
    ),
    path(
        'scales/<int:pk>/delete/',
        views.EscalaDeleteView.as_view(),
        name='escala_delete',
    ),
    path('', views.CompetenciaListView.as_view(), name='competencia_list'),
    path(
        'new/',
        views.CompetenciaCreateView.as_view(),
        name='competencia_create',
    ),
    path(
        '<int:pk>/edit/',
        views.CompetenciaUpdateView.as_view(),
        name='competencia_update',
    ),
    path(
        '<int:pk>/delete/',
        views.CompetenciaDeleteView.as_view(),
        name='competencia_delete',
    ),
    path(
        'positions/<int:pk>/profile/',
        views.CargoCompetenciaUpdateView.as_view(),
        name='cargo_competencia_update',
    ),
]
