from django.urls import path

from apps.reviews import views

app_name = 'reviews'

urlpatterns = [
    path(
        '<int:pk>/self-assessment/',
        views.SelfAssessmentView.as_view(),
        name='self_assessment',
    ),
]
