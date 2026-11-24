from django.urls import path

from . import views

app_name = "courses"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("category/<slug:slug>/", views.category_detail, name="category"),
]
