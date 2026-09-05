from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.PersonalDashboardView.as_view(), name='personal'),
    path('dashboard/team/', views.TeamDashboardView.as_view(), name='team'),
    path('dashboard/structure/', views.StructureDashboardView.as_view(), name='structure'),
    path(
        'dashboard/structure/collaborator/<int:user_pk>/drawer/',
        views.StructureCollaboratorDrawerView.as_view(),
        name='structure_collaborator_drawer',
    ),
    path('dashboard/adherence/', views.AdherenceListView.as_view(), name='adherence'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin'),
]
