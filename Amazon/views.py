from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import stripe
from django.conf import settings
from .models import Product, Category
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .forms import SignUpForm
from .cart import Cart
from django.views import View
from .models import CartItem
from django.views.decorators.csrf import csrf_exempt


# Create your views here.

def home(request):
	products = Product.objects.all()
	return render(request, 'home.html', {'products':products})

def about(request):
	return render(request, 'about.html', {})

def login_user(request):
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(username = username, password = password)
        
        if user is not None:
            
            login(request, user)
            return redirect('home')
        else:
          
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'login.html')
    return render(request, 'login.html')
	


def logout_user(request):
	logout(request)
	messages.success(request, ("You have been logged out."))
	return redirect('home')



def register_user(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')  
            return redirect('home')
        else:      
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SignUpForm()
    return render(request, 'register.html', {'form': form})



@login_required(login_url='login')  
def add_to_cart(request, product_id):
    cart = request.session.get("cart", {})

    product = Product.objects.get(id=product_id)

    if str(product_id) in cart:
        cart[str(product_id)]["quantity"] += 1
    else:
        cart[str(product_id)] = {
            "name": product.name,
            "price": int(product.price),
            "quantity": 1
        }

    request.session["cart"] = cart  
    request.session.modified = True
    return redirect("cart")

def cart_view(request):
    cart = Cart(request)
    return render(request, 'cart.html', {
        'cart_items': cart.get_items(),
        'total_price': cart.get_total_price(),
    })

def remove_from_cart(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart')

def clear_cart(request):
    if 'cart' in request.session:
        del request.session['cart']  
    return redirect('cart')  


stripe.api_key = settings.STRIPE_SECRET_KEY


def checkout(request):
    cart = request.session.get("cart", {})  

    if not cart:
        messages.error(request, "Your cart is empty!")
        return redirect("cart")


    total_price = sum(item["price"] * item["quantity"] for item in cart.values())

    if total_price <= 0:
        messages.error(request, "Invalid cart total!")
        return redirect("cart")

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'Cart Items',
                        },
                        'unit_amount': int(total_price * 100),  
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=request.build_absolute_uri('/success/'),
            cancel_url=request.build_absolute_uri('/'),
        )

        return redirect(session.url, code=303)

    except Exception as e:
        print(f"Stripe Error: {e}")  
        messages.error(request, "Payment could not be processed!")
        return redirect("cart")

def payment_cancel(request):
    return redirect("cart")


def payment_success(request):
    if 'cart' in request.session:
        del request.session['cart']
        request.session.modified = True  

    return render(request, 'success.html')


@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")
    endpoint_secret = "whsec_z7cWZEVVv7ecsLGqwiBuAtE4X8PBtvk4"
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return JsonResponse({"error": "Invalid payload"}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({"error": "Invalid signature"}, status=400)

    # Handle successful payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        request.session["cart"] = {}  # Clear the cart after successful payment

    return JsonResponse({"status": "success"}, status=200)

    




