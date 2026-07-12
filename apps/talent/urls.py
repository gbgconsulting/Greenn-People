from django.urls import path

from apps.talent import views

app_name = 'talent'

urlpatterns = [
    path('mine/', views.MyClassificationView.as_view(), name='mine'),
    path('matrix/', views.TalentMatrixView.as_view(), name='matrix'),
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
