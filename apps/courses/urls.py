from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
    path("mine/", views.my_courses, name="my_courses"),
    path("create/", views.course_create, name="create"),
    path("<int:pk>/", views.course_detail, name="detail"),
    path("<int:pk>/edit/", views.course_edit, name="edit"),
    path("<int:pk>/delete/", views.course_delete, name="delete"),
    path("<int:pk>/submit/", views.submit_for_review, name="submit"),
    path("<int:pk>/publish/", views.publish, name="publish"),
    path("<int:pk>/withdraw/", views.withdraw, name="withdraw"),
]
