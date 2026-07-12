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
    path(
        '<int:pk>/leader-assessment/',
        views.LeaderAssessmentView.as_view(),
        name='leader_assessment',
    ),
    path(
        '<int:pk>/feedbacks/',
        views.FeedbackListView.as_view(),
        name='feedback_list',
    ),
    path(
        '<int:pk>/feedbacks/new/',
        views.FeedbackCreateView.as_view(),
        name='feedback_create',
    ),
    path(
        'feedbacks/<int:pk>/acknowledge/',
        views.FeedbackAcknowledgeView.as_view(),
        name='feedback_acknowledge',
    ),
]
