from django.urls import path

from apps.organization import views

app_name = 'organization'

urlpatterns = [
    path('areas/', views.AreaListView.as_view(), name='area_list'),
    path('areas/new/', views.AreaCreateView.as_view(), name='area_create'),
    path(
        'areas/<int:pk>/edit/',
        views.AreaUpdateView.as_view(),
        name='area_update',
    ),
    path(
        'areas/<int:pk>/delete/',
        views.AreaDeleteView.as_view(),
        name='area_delete',
    ),
    path('positions/', views.CargoListView.as_view(), name='cargo_list'),
    path(
        'positions/new/',
        views.CargoCreateView.as_view(),
        name='cargo_create',
    ),
    path(
        'positions/<int:pk>/edit/',
        views.CargoUpdateView.as_view(),
        name='cargo_update',
    ),
    path(
        'positions/<int:pk>/delete/',
        views.CargoDeleteView.as_view(),
        name='cargo_delete',
    ),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path(
        'users/pending/',
        views.PendingUsersListView.as_view(),
        name='user_pending',
    ),
    path(
        'users/<int:pk>/edit/',
        views.UserUpdateView.as_view(),
        name='user_update',
    ),
    path(
        'users/<int:pk>/reassign-reports/',
        views.ReassignDirectReportsView.as_view(),
        name='user_reassign_reports',
    ),
]
