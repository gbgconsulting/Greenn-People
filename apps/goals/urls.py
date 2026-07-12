from django.urls import path

from apps.goals import views

app_name = 'goals'

urlpatterns = [
    path(
        'expectations/',
        views.ExpectationsView.as_view(),
        name='expectations',
    ),
]
