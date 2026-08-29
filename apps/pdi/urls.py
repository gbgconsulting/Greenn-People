from django.urls import path

from apps.pdi import views

app_name = 'pdi'

urlpatterns = [
    path('', views.PDIListView.as_view(), name='list'),
    path('new/', views.PDICreateView.as_view(), name='create'),
    path(
        '<int:pk>/archive/modal/',
        views.PDIArchiveModalView.as_view(),
        name='archive_modal',
    ),
    path('<int:pk>/archive/', views.PDIArchiveView.as_view(), name='archive'),
    path('<int:pk>/', views.PDIDetailView.as_view(), name='detail'),
    path(
        '<int:pk>/actions/partial/',
        views.AcaoPDIPartialListView.as_view(),
        name='action_list_partial',
    ),
    path(
        '<int:pk>/actions/create/modal/',
        views.AcaoPDICreateModalView.as_view(),
        name='action_create_modal',
    ),
    path(
        '<int:pk>/actions/',
        views.AcaoPDICreateView.as_view(),
        name='action_create',
    ),
    path(
        'actions/<int:pk>/edit/modal/',
        views.AcaoPDIUpdateModalView.as_view(),
        name='action_edit_modal',
    ),
    path(
        'actions/<int:pk>/edit/',
        views.AcaoPDIUpdateView.as_view(),
        name='action_edit',
    ),
    path(
        'actions/<int:pk>/delete/',
        views.AcaoPDIDeleteView.as_view(),
        name='action_delete',
    ),
    path(
        'actions/<int:pk>/status/',
        views.AcaoPDIStatusUpdateView.as_view(),
        name='action_status',
    ),
]
