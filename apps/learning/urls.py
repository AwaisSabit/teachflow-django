from django.urls import path

from . import views

app_name = "learning"

urlpatterns = [
    path("dashboard/", views.student_dashboard, name="student_dashboard"),
    path("teach/", views.instructor_dashboard, name="instructor_dashboard"),
    path("enrol/<int:course_pk>/", views.enrol, name="enrol"),
    path("complete/<int:lesson_pk>/", views.toggle_complete, name="toggle_complete"),
    path("lessons/<int:lesson_pk>/quiz/create/", views.quiz_create, name="quiz_create"),
    path("quizzes/<int:quiz_pk>/", views.quiz_manage, name="quiz_manage"),
    path("questions/<int:question_pk>/delete/", views.quiz_delete_question, name="quiz_delete_question"),
    path("quizzes/<int:quiz_pk>/take/", views.quiz_take, name="quiz_take"),
    path("attempts/<int:attempt_pk>/", views.quiz_result, name="quiz_result"),
]
