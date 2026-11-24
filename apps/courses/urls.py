from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("mine/", views.my_courses, name="my_courses"),
    path("create/", views.course_create, name="create"),
    path("<int:pk>/edit/", views.course_edit, name="edit"),
    path("<int:pk>/delete/", views.course_delete, name="delete"),
]
