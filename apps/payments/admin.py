"""Admin for orders."""
from django.contrib import admin

from .models import CartItem, Coupon, Order, OrderItem, WishlistItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ("code", "percent", "scope", "course", "active", "valid_from", "valid_until")
    list_filter = ("scope", "active")
    search_fields = ("code",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "order_number",
        "student",
        "total",
        "coupon",
        "discount_amount",
        "created_at",
    )
    list_filter = ("created_at", "coupon")
    search_fields = ("order_number", "student__username")
    date_hierarchy = "created_at"
    inlines = [OrderItemInline]


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "added_at")
    list_filter = ("course",)
    search_fields = ("student__username", "course__title")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("student", "course", "added_at")
    list_filter = ("course",)
    search_fields = ("student__username", "course__title")
