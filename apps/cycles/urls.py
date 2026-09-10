from django.urls import path

from apps.cycles import views

app_name = 'cycles'

urlpatterns = [
    path('', views.CicloListView.as_view(), name='ciclo_list'),
    path('new/', views.CicloCreateView.as_view(), name='ciclo_create'),
    # Antes de <int:pk>/ — governança automática (somente leitura; US4 / T023).
    path(
        'auto/governance/',
        views.AutoGovernanceView.as_view(),
        name='auto_governance',
    ),
    path(
        '<int:pk>/edit/',
        views.CicloUpdateView.as_view(),
        name='ciclo_update',
    ),
    path(
        '<int:pk>/delete/',
        views.CicloDeleteView.as_view(),
        name='ciclo_delete',
    ),
    path(
        '<int:pk>/open/',
        views.CicloOpenView.as_view(),
        name='ciclo_open',
    ),
    path(
        '<int:pk>/open/preview/',
        views.CicloOpenPreviewView.as_view(),
        name='ciclo_open_preview',
    ),
    path(
        '<int:pk>/close/',
        views.CicloCloseView.as_view(),
        name='ciclo_close',
    ),
    path(
        '<int:pk>/',
        views.CicloDetailView.as_view(),
        name='ciclo_detail',
    ),
    path(
        '<int:ciclo_pk>/objectives/',
        views.ObjetivoEstrategicoListView.as_view(),
        name='objetivo_list',
    ),
    path(
        '<int:ciclo_pk>/objectives/new/',
        views.ObjetivoEstrategicoCreateView.as_view(),
        name='objetivo_create',
    ),
    path(
        '<int:ciclo_pk>/objectives/<int:pk>/edit/',
        views.ObjetivoEstrategicoUpdateView.as_view(),
        name='objetivo_update',
    ),
    path(
        '<int:ciclo_pk>/objectives/<int:pk>/delete/',
        views.ObjetivoEstrategicoDeleteView.as_view(),
        name='objetivo_delete',
    ),
]
