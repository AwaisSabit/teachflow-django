"""Payment views: wishlist and cart.

Placeholders until the wishlist and cart commits land.
"""
from django.shortcuts import render


def wishlist(request):
    """Placeholder wishlist page."""
    return render(
        request,
        "coming_soon.html",
        {"title": "My wishlist", "message": "Your wishlist is coming soon."},
    )


def cart(request):
    """Placeholder cart page."""
    return render(
        request,
        "coming_soon.html",
        {"title": "My cart", "message": "Your cart is coming soon."},
    )
