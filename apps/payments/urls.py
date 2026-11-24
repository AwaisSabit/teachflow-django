from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("wishlist/", views.wishlist, name="wishlist"),
    path("cart/", views.cart, name="cart"),
    path("checkout/course/<int:course_pk>/", views.checkout_course, name="checkout_course"),
    path("wishlist/add/<int:course_pk>/", views.wishlist_add, name="wishlist_add"),
    path("wishlist/remove/<int:course_pk>/", views.wishlist_remove, name="wishlist_remove"),
    path("cart/add/<int:course_pk>/", views.cart_add, name="cart_add"),
    path("cart/remove/<int:course_pk>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout_cart, name="checkout_cart"),
    path("coupon/apply/", views.apply_coupon, name="apply_coupon"),
    path("coupon/remove/", views.remove_coupon, name="remove_coupon"),
    path("history/", views.purchase_history, name="history"),
    path("earnings/", views.earnings_report, name="earnings_report"),
]
