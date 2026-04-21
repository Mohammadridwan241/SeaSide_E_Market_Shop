from django.shortcuts import render, redirect, get_object_or_404
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt

from .forms import (
    RegistrationForm,
    RatingForm,
    CheckoutForm,
    PasswordResetRequestForm,
    PasswordResetCodeForm,
    ProductForm,
    ProductUpdateForm,
    FrontendOrderStatusForm,
)
from .models import (
    Category,
    Product,
    Cart,
    CartItem,
    Rating,
    Order,
    OrderItem,
    PasswordResetCode,
    INSIDE_CHATTOGRAM_SHIPPING_FEE,
    OUTSIDE_CHATTOGRAM_SHIPPING_FEE,
    get_shipping_fee_for_city,
)
from django.db.models import Q, Min, Max, Avg
from .sslcommerz import (
    SSLCommerzError,
    create_payment_session,
    send_order_confirmation_email,
    validate_payment,
)


def is_frontend_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


frontend_admin_required = user_passes_test(is_frontend_admin, login_url='login')


def _build_transaction_id(order):
    return f'SSLCZ-ORDER-{order.id}-{int(timezone.now().timestamp())}'


def _reduce_order_stock(order):
    if order.stock_reduced:
        return

    for item in order.order_items.select_related('product'):
        product = item.product
        product.stock = max(product.stock - item.quantity, 0)
        product.save(update_fields=['stock'])

    order.stock_reduced = True
    order.save(update_fields=['stock_reduced'])


def _restore_order_stock(order):
    if not order.stock_reduced:
        return

    for item in order.order_items.select_related('product'):
        product = item.product
        product.stock += item.quantity
        product.save(update_fields=['stock'])

    order.stock_reduced = False
    order.save(update_fields=['stock_reduced'])


@transaction.atomic
def _create_order_from_cart(form, user, cart, payment_method):
    order = form.save(commit=False)
    order.user = user
    order.status = 'pending'
    order.payment_method = payment_method
    order.shipping_fee = get_shipping_fee_for_city(form.cleaned_data['city'])
    order.transaction_id = ''
    order.sslcommerz_session_key = ''
    order.validation_id = ''
    order.bank_transaction_id = ''

    if payment_method == 'cod':
        order.payment_status = 'cod'
        order.paid = False
    else:
        order.payment_status = 'pending'
        order.paid = False

    order.save()

    for item in cart.items.select_related('product'):
        OrderItem.objects.create(
            order=order,
            product=item.product,
            price=item.product.price,
            quantity=item.quantity,
        )

    return order


@transaction.atomic
def _finalize_cod_order(order, cart):
    order.transaction_id = 'COD'
    order.save(update_fields=['transaction_id'])
    _reduce_order_stock(order)
    cart.items.all().delete()
    send_order_confirmation_email(order)


@transaction.atomic
def _mark_order_payment_failed(order):
    if order.payment_status == 'paid':
        return

    order.payment_status = 'failed'
    order.status = 'failed'
    order.paid = False
    order.save(update_fields=['payment_status', 'status', 'paid'])


@transaction.atomic
def _mark_order_payment_canceled(order):
    if order.payment_status == 'paid':
        return

    order.payment_status = 'canceled'
    order.status = 'canceled'
    order.paid = False
    order.save(update_fields=['payment_status', 'status', 'paid'])


@transaction.atomic
def _mark_order_payment_success(order, validation_data=None, clear_cart=False):
    was_paid = order.payment_status == 'paid'

    order.payment_status = 'paid'
    order.status = 'confirm'
    order.paid = True

    if validation_data:
        order.validation_id = validation_data.get('val_id', '') or order.validation_id
        order.bank_transaction_id = validation_data.get('bank_tran_id', '') or order.bank_transaction_id
        order.transaction_id = validation_data.get('tran_id', '') or order.transaction_id
        order.sslcommerz_session_key = validation_data.get('sessionkey', '') or order.sslcommerz_session_key

    order.save(update_fields=[
        'payment_status',
        'status',
        'paid',
        'validation_id',
        'bank_transaction_id',
        'transaction_id',
        'sslcommerz_session_key',
    ])

    _reduce_order_stock(order)

    if clear_cart:
        CartItem.objects.filter(cart__user=order.user).delete()

    if not was_paid:
        send_order_confirmation_email(order)


def _unique_product_slug(name):
    base_slug = slugify(name) or 'product'
    slug = base_slug
    counter = 1

    while Product.objects.filter(slug=slug).exists():
        counter += 1
        slug = f'{base_slug}-{counter}'

    return slug
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


def password_reset_request_view(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email__iexact=email)
            except User.DoesNotExist:
                messages.warning(request, 'No account found with that email address.')
            else:
                PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
                reset_code = PasswordResetCode.objects.create(user=user)
                try:
                    send_mail(
                        subject='Your SeaSide-E-market password reset code',
                        message=(
                            f'Hello {user.get_full_name() or user.username},\n\n'
                            f'Your password reset code is: {reset_code.code}\n'
                            'This code will expire in 10 minutes.\n\n'
                            'If you did not request this reset, please ignore this email.'
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=False,
                    )
                except Exception:
                    reset_code.is_used = True
                    reset_code.save(update_fields=['is_used'])
                    messages.error(request, 'We could not send the reset code right now. Please try again shortly.')
                else:
                    request.session['password_reset_user_id'] = user.id
                    messages.success(request, 'A reset code has been sent to your email.')
                    return redirect('password_reset_verify')
    else:
        form = PasswordResetRequestForm()

    return render(request, 'SeaSide_Shop/password_reset_request.html', {'form': form})


def password_reset_verify_view(request):
    user_id = request.session.get('password_reset_user_id')
    if not user_id:
        messages.warning(request, 'Please enter your email first.')
        return redirect('password_reset_request')

    user = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        form = PasswordResetCodeForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data['code']
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                is_used=False,
                expires_at__gte=timezone.now(),
            ).order_by('-created_at').first()

            if not reset_code:
                messages.error(request, 'Invalid or expired reset code.')
            else:
                user.set_password(form.cleaned_data['new_password1'])
                user.save(update_fields=['password'])
                reset_code.is_used = True
                reset_code.save(update_fields=['is_used'])
                PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)
                request.session.pop('password_reset_user_id', None)
                messages.success(request, 'Your password has been reset successfully.')
                return redirect('login')
    else:
        form = PasswordResetCodeForm()

    return render(request, 'SeaSide_Shop/password_reset_verify.html', {
        'form': form,
        'reset_email': user.email,
    })


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
    selected_payment_method = 'cod'
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        selected_city = request.POST.get('city', '').strip()
        selected_payment_method = request.POST.get('payment_method', 'cod')
        if selected_city:
            shipping_fee = get_shipping_fee_for_city(selected_city)
        if form.is_valid():
            selected_payment_method = form.cleaned_data['payment_method']
            order = _create_order_from_cart(form, request.user, cart, selected_payment_method)

            if selected_payment_method == 'cod':
                _finalize_cod_order(order, cart)
                messages.success(request, 'Order placed with Cash on Delivery')
                return render(request, 'SeaSide_Shop/payment_success.html', {'order': order})

            order.transaction_id = _build_transaction_id(order)
            order.save(update_fields=['transaction_id'])

            try:
                payment_data = create_payment_session(request, order)
            except SSLCommerzError as exc:
                _mark_order_payment_failed(order)
                messages.error(request, str(exc))
            else:
                order.sslcommerz_session_key = payment_data.get('sessionkey', '')
                order.save(update_fields=['sslcommerz_session_key'])
                return redirect(payment_data['GatewayPageURL'])
    else:
        form = CheckoutForm(initial={'payment_method': 'cod'})

    if shipping_fee is None and form.is_bound:
        selected_city = form.data.get('city', '').strip()
        if selected_city:
            shipping_fee = get_shipping_fee_for_city(selected_city)

    if form.is_bound:
        selected_payment_method = form.data.get('payment_method', 'cod')
    else:
        selected_payment_method = form.initial.get('payment_method', 'cod')

    order_total = cart.get_total_price() + (shipping_fee or 0)

    return render(request, 'SeaSide_Shop/checkout.html', {
        'cart' : cart,
        'form' : form,
        'shipping_fee': shipping_fee,
        'order_total': order_total,
        'inside_chattogram_fee': INSIDE_CHATTOGRAM_SHIPPING_FEE,
        'outside_chattogram_fee': OUTSIDE_CHATTOGRAM_SHIPPING_FEE,
        'selected_payment_method': selected_payment_method,
    })


def _get_order_from_gateway_request(request):
    tran_id = request.POST.get('tran_id') or request.GET.get('tran_id')
    return get_object_or_404(Order, transaction_id=tran_id)


@csrf_exempt
def sslcommerz_success(request):
    order = _get_order_from_gateway_request(request)
    val_id = request.POST.get('val_id') or request.GET.get('val_id')

    if order.payment_status == 'paid':
        messages.success(request, 'Payment Successful')
        return render(request, 'SeaSide_Shop/payment_success.html', {'order': order})

    try:
        validation_data = validate_payment(val_id, order.get_total_cost())
    except SSLCommerzError:
        _mark_order_payment_failed(order)
        messages.error(request, 'We could not validate your payment. Please contact support.')
        return render(request, 'SeaSide_Shop/payment_failed.html', {'order': order})

    _mark_order_payment_success(order, validation_data=validation_data, clear_cart=True)
    messages.success(request, 'Payment Successful')
    return render(request, 'SeaSide_Shop/payment_success.html', {'order': order})


@csrf_exempt
def sslcommerz_fail(request):
    order = _get_order_from_gateway_request(request)
    _mark_order_payment_failed(order)
    messages.error(request, 'Payment failed. Please try again.')
    return render(request, 'SeaSide_Shop/payment_failed.html', {'order': order})


@csrf_exempt
def sslcommerz_cancel(request):
    order = _get_order_from_gateway_request(request)
    _mark_order_payment_canceled(order)
    messages.warning(request, 'Payment was cancelled.')
    return render(request, 'SeaSide_Shop/payment_cancelled.html', {'order': order})


@csrf_exempt
def sslcommerz_ipn(request):
    order = _get_order_from_gateway_request(request)
    val_id = request.POST.get('val_id')

    if request.method != 'POST':
        return render(request, 'SeaSide_Shop/payment_ipn.html', {'message': 'Invalid IPN request.'}, status=400)

    if order.payment_status == 'paid':
        return render(request, 'SeaSide_Shop/payment_ipn.html', {'message': 'Payment already processed.'})

    try:
        validation_data = validate_payment(val_id, order.get_total_cost())
    except SSLCommerzError:
        _mark_order_payment_failed(order)
        return render(request, 'SeaSide_Shop/payment_ipn.html', {'message': 'Payment validation failed.'}, status=400)

    _mark_order_payment_success(order, validation_data=validation_data, clear_cart=True)
    return render(request, 'SeaSide_Shop/payment_ipn.html', {'message': 'IPN processed successfully.'})


@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    if request.method == 'POST' and order.status == 'pending':
        _restore_order_stock(order)
        order.status = 'canceled'
        order.payment_status = 'canceled'
        order.save(update_fields=['status', 'payment_status', 'paid'])
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
    total_spent = sum(
        order.get_total_cost()
        for order in orders.exclude(status__in=['canceled', 'failed']).exclude(payment_status__in=['canceled', 'failed'])
    )
    order_history_active = (tab == 'orders') # true or false return korbe
    
    return render(request, 'SeaSide_Shop/profile.html', {
        'user' : request.user,
        'orders' : orders,
        'completed_orders' : completed_orders,
        'completed_orders_count' : completed_orders_count,
        'total_spent' : total_spent,
        'order_history_active' : order_history_active
    })


@frontend_admin_required
def frontend_admin_dashboard(request):
    orders = Order.objects.select_related('user').prefetch_related(
        'order_items__product',
        'order_items__product__category',
    ).order_by('-created_at')
    products = Product.objects.select_related('category').order_by('-created_at')

    status_filter = request.GET.get('status', '')
    payment_filter = request.GET.get('payment_status', '')

    if status_filter:
        orders = orders.filter(status=status_filter)
    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)

    stats_orders = Order.objects.all()
    context = {
        'orders': orders,
        'status_choices': Order.STATUS,
        'payment_status_choices': Order.PAYMENT_STATUS,
        'selected_status': status_filter,
        'selected_payment_status': payment_filter,
        'total_orders': stats_orders.count(),
        'pending_orders': stats_orders.filter(status='pending').count(),
        'paid_orders': stats_orders.filter(Q(paid=True) | Q(payment_status='paid')).distinct().count(),
        'total_products': Product.objects.filter(available=True).count(),
        'removed_products': Product.objects.filter(available=False).count(),
        'products': products,
    }
    return render(request, 'SeaSide_Shop/frontend_admin/dashboard.html', context)


@frontend_admin_required
def frontend_admin_update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)

    if request.method == 'POST':
        old_status = order.status
        old_payment_status = order.payment_status
        form = FrontendOrderStatusForm(request.POST, instance=order)
        if form.is_valid():
            updated_order = form.save(commit=False)

            if updated_order.status == 'canceled':
                _restore_order_stock(updated_order)
                updated_order.payment_status = 'canceled'
                updated_order.paid = False
            elif updated_order.status == 'failed':
                updated_order.payment_status = 'failed'
                updated_order.paid = False
            elif updated_order.status == 'delivered':
                updated_order.payment_status = 'paid'
                updated_order.paid = True
            elif updated_order.payment_status == 'paid':
                updated_order.paid = True
            elif updated_order.payment_status in ['cod', 'pending', 'failed', 'canceled']:
                updated_order.paid = False

            updated_order.save()

            if old_status != updated_order.status or old_payment_status != updated_order.payment_status:
                messages.success(request, f'Order #{updated_order.id} updated successfully.')
            else:
                messages.info(request, f'Order #{updated_order.id} already has those statuses.')
        else:
            messages.error(request, 'Order status could not be updated.')

    return redirect('frontend_admin_dashboard')


@frontend_admin_required
def frontend_admin_add_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product_name = form.cleaned_data['name'].strip()
            existing_product = Product.objects.filter(name__iexact=product_name).first()

            if existing_product:
                added_stock = form.cleaned_data['stock']
                existing_product.stock += added_stock
                existing_product.available = True
                existing_product.save(update_fields=['stock', 'available'])
                messages.success(
                    request,
                    f'{existing_product.name} already exists. Stock increased by {added_stock}. New stock: {existing_product.stock}.'
                )
                return redirect('frontend_admin_dashboard')

            product = form.save(commit=False)
            product.name = product_name
            product.slug = _unique_product_slug(product.name)
            product.save()
            messages.success(request, f'{product.name} has been added successfully.')
            return redirect('frontend_admin_dashboard')
    else:
        form = ProductForm()

    return render(request, 'SeaSide_Shop/frontend_admin/add_product.html', {'form': form})


@frontend_admin_required
def frontend_admin_remove_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        if product.available:
            product.available = False
            product.save(update_fields=['available'])
            messages.success(request, f'{product.name} has been removed from the store.')
        else:
            messages.info(request, f'{product.name} is already removed from the store.')

    return redirect('frontend_admin_dashboard')


@frontend_admin_required
def frontend_admin_update_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        form = ProductUpdateForm(request.POST, instance=product)
        if form.is_valid():
            updated_product = form.save()
            messages.success(
                request,
                f'{updated_product.name} updated successfully. Price: ৳{updated_product.price}, Stock: {updated_product.stock}.'
            )
        else:
            error_text = ' '.join(
                error
                for errors in form.errors.values()
                for error in errors
            )
            messages.error(request, error_text or 'Product could not be updated.')

    return redirect('frontend_admin_dashboard')
