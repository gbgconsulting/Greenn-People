from django.urls import path

from apps.cycles import views

app_name = 'cycles'

urlpatterns = [
    path('', views.CicloListView.as_view(), name='ciclo_list'),
    path('new/', views.CicloCreateView.as_view(), name='ciclo_create'),
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
        '<int:pk>/close/',
        views.CicloCloseView.as_view(),
        name='ciclo_close',
    ),
]
