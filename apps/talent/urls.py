from django.urls import path

from apps.talent import views

app_name = 'talent'

urlpatterns = [
    path('mine/', views.MyClassificationView.as_view(), name='mine'),
    path('matrix/', views.TalentMatrixView.as_view(), name='matrix'),
    path(
        'matrix/drawer/<int:user_pk>/',
        views.MatrixDrawerView.as_view(),
        name='matrix_drawer',
    ),
    path(
        'matrix/potencial/<int:user_pk>/',
        views.MatrixPotencialView.as_view(),
        name='matrix_potencial',
    ),
    path(
        'matrix/move/<int:user_pk>/',
        views.MatrixMoveView.as_view(),
        name='matrix_move',
    ),
    path(
        '<int:user_pk>/classify/',
        views.ClassifyTalentView.as_view(),
        name='classify',
    ),
    path(
        '<int:pk>/toggle-visibility/',
        views.ToggleVisibilityView.as_view(),
        name='toggle_visibility',
    ),
]
