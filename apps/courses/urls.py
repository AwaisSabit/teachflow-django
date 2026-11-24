from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("mine/", views.my_courses, name="my_courses"),
    path("create/", views.course_create, name="create"),
    path("<int:pk>/", views.course_detail, name="detail"),
    path("<int:pk>/review/", views.add_review, name="review"),
    path("<int:pk>/edit/", views.course_edit, name="edit"),
    path("<int:pk>/delete/", views.course_delete, name="delete"),
    path("<int:pk>/submit/", views.submit_for_review, name="submit"),
    path("<int:pk>/publish/", views.publish, name="publish"),
    path("<int:pk>/withdraw/", views.withdraw, name="withdraw"),
    path("<int:course_pk>/sections/create/", views.section_create, name="section_create"),
    path("sections/<int:pk>/edit/", views.section_edit, name="section_edit"),
    path("sections/<int:pk>/delete/", views.section_delete, name="section_delete"),
    path("sections/<int:section_pk>/lessons/create/", views.lesson_create, name="lesson_create"),
    path("lessons/<int:pk>/edit/", views.lesson_edit, name="lesson_edit"),
    path("lessons/<int:pk>/delete/", views.lesson_delete, name="lesson_delete"),
    path("lessons/<int:pk>/", views.lesson_detail, name="lesson_detail"),
]
