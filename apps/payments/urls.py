from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("wishlist/", views.wishlist, name="wishlist"),
    path("cart/", views.cart, name="cart"),
]
