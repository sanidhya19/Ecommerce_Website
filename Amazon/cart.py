from decimal import Decimal
from django.conf import settings
from Amazon.models import Product  # Ensure this is correct

class Cart:
    def __init__(self, request):
        """Initialize the cart using session data."""
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)

        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}

        self.cart = cart

    def add(self, product_id, product_data):
        self.cart[product_id] = product_data
        self.session['cart'] = self.cart
        self.session.modified = True

    def save(self):
        """Mark session as modified to ensure it saves changes."""
        self.session.modified = True

    def remove(self, product):
        """Remove a product from the cart."""
        product_id = str(product.id)

        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def get_items(self):
        for item in self.cart.values():
            item['total_price'] = Decimal(item.get('price', 0)) * item.get('quantity', 1)
        return self.cart.values()

    def get_total_price(self):
        return sum(Decimal(item.get('price', 0)) * item.get('quantity', 1) for item in self.cart.values())

    def clear(self):
        del self.session[settings.CART_SESSION_ID]
        self.save()
