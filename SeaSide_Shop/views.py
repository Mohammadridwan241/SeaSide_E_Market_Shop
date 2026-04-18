from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .forms import RegistrationForm, RatingForm, CheckoutForm
from .models import (
    Category,
    Product,
    Cart,
    CartItem,
    Rating,
    Order,
    OrderItem,
    INSIDE_CHATTOGRAM_SHIPPING_FEE,
    OUTSIDE_CHATTOGRAM_SHIPPING_FEE,
    get_shipping_fee_for_city,
)
from django.db.models import Q, Min, Max, Avg
from django.contrib.auth.decorators import login_required
from .sslcommerz import send_order_confirmation_email
# Create your views here.

# Manual User Authentication
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "Logged In Successful!")
            return redirect('profile')
        else:
            messages.error(request, "Invalid username or password") 
    return render(request, 'SeaSide_Shop/login.html')

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        
        if form.is_valid():
            user = form.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, "Registration Successful!")
            return redirect('profile')
    else:
        form = RegistrationForm()
    
    return render(request, 'SeaSide_Shop/register.html', {'form' : form})

def logout_view(request):
    logout(request)
    return redirect('login')


# homepage
def home(request):
    featured_products = Product.objects.filter(available=True).order_by('-created_at')[:8] # descending order
    categories = Category.objects.all()
    
    return render(request, 'SeaSide_Shop/home.html', {'featured_products' : featured_products, 'categories' : categories})

# product list page
def product_list(request, category_slug = None):
    category = None 
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        print("category .......", category)
        products = products.filter(category = category)
        
    min_price = products.aggregate(Min('price'))['price__min']
    max_price = products.aggregate(Max('price'))['price__max']
    
    if request.GET.get('min_price'):
        products = products.filter(price__gte=request.GET.get('min_price'))
    
    if request.GET.get('max_price'):
        products = products.filter(price__lte=request.GET.get('max_price'))
    
    if request.GET.get('rating'):
        min_rating = request.GET.get('rating')
        products = products.annotate(avg_rating = Avg('ratings__rating')).filter(avg_rating__gte=min_rating)
        # temp variable --> avg_rating
        # Avg
        # ratings related_name ke use kore rating model er rating value ke access korlam
        # avg_rating == user er filter kora rating er sathe
        
    
    if request.GET.get('search'):
        query = request.GET.get('search')
        products = products.filter(
            Q(name__icontains = query) | 
            Q(description__icontains = query) | 
            Q(category__name__icontains = query)  
        )
    
    return render(request, 'SeaSide_Shop/product_list.html', {
        'category' : category,
        'categories' : categories,
        'products' : products,
        'min_price' : min_price,
        'max_price' : max_price
    })

# product detail page
def product_detail(request, slug):
    product = get_object_or_404(Product, slug = slug, available = True)
    related_products = Product.objects.filter(category = product.category).exclude(id=product.id)
    
    user_rating = None 
    
    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(product=product, user=request.user)
        except Rating.DoesNotExist:
            pass 
        
    rating_form = RatingForm(instance=user_rating)
    
    return render(request, 'SeaSide_Shop/product_detail.html', {
        'product' :product,
        'related_products' : related_products,
        'user_rating' : user_rating,
        'rating_form' : rating_form
    })

# Rate Product 
# logged in user, Purchase koreche kina
@login_required
def rate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_staff or request.user.is_superuser:
        messages.warning(request, 'Admin accounts cannot give reviews.')
        return redirect('product_detail', slug=product.slug)
    
    ordered_items = OrderItem.objects.filter(
        order__user = request.user,
        product = product,
        order__paid = True
    )
    
    if not ordered_items.exists(): # order kore nai
        messages.warning(request, 'You can only rate products you have purchased!')
        return redirect('product_detail', slug=product.slug)
    
    try:
        rating = Rating.objects.get(product=product, user = request.user)
    except Rating.DoesNotExist:
        rating = None 
    
    # jodi rating age diye thake tail rating form ager rating data diye fill up kora thakbe sekhtre instance = user rating hoye jbe
    # jodi rating na kora thake taile instance = None thakbe and se new rating create korte parbe
    if request.method == 'POST':
        form = RatingForm(request.POST, instance = rating) 
        if form.is_valid():
            rating = form.save(commit=False)
            rating.product = product
            rating.user = request.user 
            rating.save()
            return redirect('product_detail', slug=product.slug)
    else:
        form = RatingForm(instance=rating)
    
    return render(request, 'SeaSide_Shop/rate_product.html', {
        'form' : form,
        'product' : product
    })

# Everything about cart - feature
# cart detail --> temporary order - ok
# cart e item add - ok
# cart e item remove - ok
# cart e item update - ok
# checkout - ok

@login_required
def cart_detail(request):
    # user er kono cart nai
    # user er cart ache
    try:
        cart = Cart.objects.get(user=request.user)
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
    
    return render(request, 'SeaSide_Shop/cart.html', {'cart' : cart})

# cart add
@login_required
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    # User er cart ache kina
    
    # Exception handling
    # jodi thake taile oi cart ta check korbo
    try: # ekahne error aste pare
        cart = Cart.objects.get(user=request.user)
    
    # jodi na thake, taile cart ekta banabo
    except Cart.DoesNotExist:
        cart = Cart.objects.create(user=request.user)
    
    # Cart e item add korbo
    # item already cart e ache
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.quantity += 1
        cart_item.save()
        
    # item cart e nai
    except CartItem.DoesNotExist:
        CartItem.objects.create(cart=cart, product=product, quantity = 1)
    
    messages.success(request, f"{product.name} has been added to your cart!")
    return redirect('product_detail', slug=product.slug)
    

# cart Update
# cart item quantity increase/decrease korte parbo
@login_required
def cart_update(request, product_id):
    # cart konta
    # cart er item konta
    # main product jeta cart item hisebe cart e ache
    
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    
    quantity = int(request.POST.get('quantity', 1))
    
    # Keya saban -> stock e ache 20 ta product
    # user Keya saban -> 40 ta add to cart korche..
    # user Keya saban -> 5, 4, 3, 2, 1, 0 --> cartitem delete kore deoya lagbe
    
    if quantity <= 0:
        cart_item.delete()
        messages.success(request, f"{product.name} has been removed from your cart!")
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, f"Cart updated successfully!!")
    return redirect('cart_detail')

@login_required
def cart_remove(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)

    cart_item.delete()
    messages.success(request, f"{product.name} has been removed from your cart!")
    return redirect("cart_detail")

# 80% --> thinking
# 20% time --> coding


# checkout
# cart er data gula niye asbo
# ['first_name', 'last_name', 'email', 'address', 'postal_code', 'city','note']
# TOTAL TAKA --> 8000 TAKA
# Payment option --> Payment gateway te niye jabo

# Product --> Cart Item --> Order Item
@login_required
def checkout(request):
    try:
        cart = Cart.objects.get(user=request.user)
        if not cart.items.exists():
            messages.warning(request, 'Your cart is empty!')
            return redirect('cart_detail')
    except Cart.DoesNotExist:
        messages.warning(request, 'Your cart is empty!')
        return redirect('cart_detail')
    
    # Checkout form ta fill up korbe
    shipping_fee = None
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        selected_city = request.POST.get('city', '').strip()
        if selected_city:
            shipping_fee = get_shipping_fee_for_city(selected_city)
        if form.is_valid():
            order = form.save(commit=False) # form object create hobe kintu data database e jabe na
            order.user = request.user 
            order.status = 'pending'
            order.payment_method = 'cod'
            order.transaction_id = ''
            order.shipping_fee = get_shipping_fee_for_city(form.cleaned_data['city'])
            order.save() # order kora hoye geche

            for item in cart.items.all():
                OrderItem.objects.create(
                    order = order,
                    product = item.product, # cartitem e ekhn order item
                    price = item.product.price, # product er main price e order item er main price
                    quantity = item.quantity # cart item er quantity e hocche order item er quantity
                )
            order.transaction_id = 'COD'
            order.save(update_fields=['transaction_id'])

            for item in order.order_items.all():
                product = item.product
                product.stock = max(product.stock - item.quantity, 0)
                product.save(update_fields=['stock'])

            cart.items.all().delete()
            send_order_confirmation_email(order)
            messages.success(request, 'Order placed with Cash on Delivery')
            return render(request, 'SeaSide_Shop/payment_success.html', {'order': order})
    else:
        form = CheckoutForm()

    if shipping_fee is None and form.is_bound:
        selected_city = form.data.get('city', '').strip()
        if selected_city:
            shipping_fee = get_shipping_fee_for_city(selected_city)

    order_total = cart.get_total_price() + (shipping_fee or 0)

    return render(request, 'SeaSide_Shop/checkout.html', {
        'cart' : cart,
        'form' : form,
        'shipping_fee': shipping_fee,
        'order_total': order_total,
        'inside_chattogram_fee': INSIDE_CHATTOGRAM_SHIPPING_FEE,
        'outside_chattogram_fee': OUTSIDE_CHATTOGRAM_SHIPPING_FEE,
    })


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST' and order.status == 'pending':
        for item in order.order_items.select_related('product'):
            product = item.product
            product.stock += item.quantity
            product.save(update_fields=['stock'])
        order.status = 'canceled'
        order.save(update_fields=['status', 'paid'])
        messages.success(request, 'Order canceled successfully')
    elif order.status != 'pending':
        messages.warning(request, 'Only pending orders can be canceled')
    return redirect('profile')


# profile page

@login_required
def profile(request):
    tab = request.GET.get('tab')
    orders = Order.objects.filter(user = request.user)
    completed_orders = orders.filter(status = 'delivered')
    completed_orders_count = completed_orders.count()
    total_spent = sum(order.get_total_cost() for order in orders.exclude(status='canceled'))
    order_history_active = (tab == 'orders') # true or false return korbe
    
    return render(request, 'SeaSide_Shop/profile.html', {
        'user' : request.user,
        'orders' : orders,
        'completed_orders' : completed_orders,
        'completed_orders_count' : completed_orders_count,
        'total_spent' : total_spent,
        'order_history_active' : order_history_active
    })
