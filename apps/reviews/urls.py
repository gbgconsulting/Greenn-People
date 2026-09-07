from django.urls import path

from apps.reviews import views

app_name = 'reviews'

urlpatterns = [
    path(
        '',
        views.AvaliacaoListView.as_view(),
        name='list',
    ),
    path(
        'feedbacks/continuo/',
        views.ContinuousFeedbackMineRedirectView.as_view(),
        name='continuous_feedback_mine',
    ),
    path(
        'feedbacks/continuo/<int:pk>/acknowledge/',
        views.ContinuousFeedbackAcknowledgeView.as_view(),
        name='continuous_feedback_acknowledge',
    ),
    path(
        'usuarios/<int:user_id>/feedbacks/continuo/',
        views.ContinuousFeedbackListView.as_view(),
        name='continuous_feedback_list',
    ),
    path(
        'usuarios/<int:user_id>/feedbacks/continuo/new/',
        views.ContinuousFeedbackCreateView.as_view(),
        name='continuous_feedback_create',
    ),
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
    # Detalhe por último entre rotas ``<pk>/…`` para não capturar sub-paths.
    path(
        '<int:pk>/',
        views.AvaliacaoDetailView.as_view(),
        name='detail',
    ),
]
