from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health),
    path("skills", views.list_skills),
    path("skills/execute", views.execute_skill),
]
