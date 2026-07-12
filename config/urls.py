"""
URL configuration for Greenn People.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('organization/', include('apps.organization.urls')),
    path('competencies/', include('apps.competencies.urls')),
    path('goals/', include('apps.goals.urls')),
    # PersonalDashboardView em `/`; demais rotas do app sob `/dashboard/...`
    path('', include('apps.dashboard.urls')),
]
