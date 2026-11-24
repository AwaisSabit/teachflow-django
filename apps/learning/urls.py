from django.urls import path

from . import views

app_name = "learning"

urlpatterns = [
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("teach/", views.instructor_dashboard, name="instructor_dashboard"),
]
