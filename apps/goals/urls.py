from django.urls import path

from apps.goals import views

app_name = 'goals'

urlpatterns = [
    path(
        'expectations/',
        views.ExpectationsView.as_view(),
        name='expectations',
    ),
    path('', views.MetaListView.as_view(), name='meta_list'),
    path('new/', views.MetaCreateView.as_view(), name='meta_create'),
    path(
        '<int:pk>/edit/',
        views.MetaUpdateView.as_view(),
        name='meta_update',
    ),
    path(
        '<int:pk>/delete/',
        views.MetaDeleteView.as_view(),
        name='meta_delete',
    ),
    path(
        '<int:pk>/progress/',
        views.MetaProgressUpdateView.as_view(),
        name='meta_progress',
    ),
]
