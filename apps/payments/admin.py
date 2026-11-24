"""Admin for orders."""
from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_number", "student", "total", "created_at")
    list_filter = ("created_at",)
    search_fields = ("order_number", "student__username")
    inlines = [OrderItemInline]
