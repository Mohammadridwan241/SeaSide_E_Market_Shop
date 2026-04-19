from datetime import timedelta
from decimal import Decimal
import random

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


INSIDE_CHATTOGRAM_SHIPPING_FEE = Decimal('80.00')
OUTSIDE_CHATTOGRAM_SHIPPING_FEE = Decimal('120.00')


def get_shipping_fee_for_city(city):
    normalized_city = (city or '').strip().lower()
    if normalized_city in {'chattogram', 'chittagong'}:
        return INSIDE_CHATTOGRAM_SHIPPING_FEE
    return OUTSIDE_CHATTOGRAM_SHIPPING_FEE


# Create your models here.
# Category Model
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField()

    class Meta:
        verbose_name_plural = 'Categories'
        
    def __str__(self):
        return self.name 

class Product(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2) # 405.99
    stock = models.PositiveBigIntegerField(default=1)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    image = models.ImageField(upload_to='products/%Y/%m/%d') # products/25/10/2025
    
    def __str__(self):
        return self.name 
    
    # rating dekhte pan 
    # 1 ta product 10 jon kinche --> 5 jon rating . 4.0, 5.0. 3.5, 2.5 , 4.0
    
    def average_rating(self):
        ratings = self.ratings.all()
        if ratings.count() > 0:
            return sum([i.rating for i in ratings])/ratings.count()
        return 0

class Rating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} - {self.rating}"
    
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # total price
    def get_total_price(self):
        return sum(item.get_cost() for item in self.items.all()) # 100
    # total koita item
    def get_total_items(self):
        return sum(item.quantity for item in self.items.all()) 
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE) 
    quantity = models.PositiveBigIntegerField(default=1)
    
    def __str__(self):
        return f"{self.quantity} X {self.product.name}" # 4 X Shirt
    def get_cost(self):
        return self.quantity*self.product.price  # 20
    
class Order(models.Model):
    STATUS = [
        ('pending', 'Pending'),
        ('confirm', 'Confirmed'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('canceled', 'Cancelled'),
    ]
    PAYMENT_METHODS = [
        ('cod', 'Cash on Delivery'),
        ('sslcommerz', 'Pay Online with SSLCommerz'),
    ]
    PAYMENT_STATUS = [
        ('cod', 'Pending/COD'),
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('canceled', 'Cancelled'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    address = models.TextField()
    postal_code = models.CharField(max_length=100)
    phone = models.CharField(max_length=12, blank=True)
    city = models.CharField(max_length=100)
    note = models.TextField(blank=True)
    shipping_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    paid = models.BooleanField(default=False)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='cod')
    transaction_id = models.CharField(max_length=100, blank=True)
    sslcommerz_session_key = models.CharField(max_length=255, blank=True)
    validation_id = models.CharField(max_length=255, blank=True)
    bank_transaction_id = models.CharField(max_length=255, blank=True)
    stock_reduced = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS, default='pending')
    
    def __str__(self):
        return f"Order #{self.id}" # Order #2

    def save(self, *args, **kwargs):
        if self.status == 'delivered':
            self.paid = True
            self.payment_status = 'paid'
        super().save(*args, **kwargs)

    def get_items_total(self):
        return sum(item.get_cost() for item in self.order_items.all())

    # order item er sum lagbe
    def get_total_cost(self):
        return self.get_items_total() + self.shipping_fee

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def get_cost(self):
        return self.quantity*self.price  # 20


class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_codes')
    code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def __str__(self):
        return f"{self.user.username} - {self.code}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"{random.randint(0, 999999):06d}"
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at
