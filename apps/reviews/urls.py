from django.urls import path

from apps.reviews import views

app_name = 'reviews'

urlpatterns = [
    path(
        '<int:pk>/advance/',
        views.AdvanceStageView.as_view(),
        name='advance',
    ),
    path(
        '<int:pk>/self-assessment/',
        views.SelfAssessmentView.as_view(),
        name='self_assessment',
    ),
]
