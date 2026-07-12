from django.urls import path

from apps.dashboard import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.PersonalDashboardView.as_view(), name='personal'),
    path('dashboard/team/', views.TeamDashboardView.as_view(), name='team'),
    path('dashboard/adherence/', views.AdherenceListView.as_view(), name='adherence'),
    path('dashboard/admin/', views.AdminDashboardView.as_view(), name='admin'),
]
