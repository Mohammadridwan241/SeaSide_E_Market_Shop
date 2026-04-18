from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    # Authentication related urls
    path('login/', views.login_view, name="login"),
    path('register/', views.register_view, name="register"),
    path('logout/', views.logout_view, name="logout"),
    path('password-reset/', views.password_reset_request_view, name="password_reset_request"),
    path('password-reset/verify/', views.password_reset_verify_view, name="password_reset_verify"),
    
    # products related urls
    path('', views.home, name="home"),
    path('products/', views.product_list, name="product_list"),
    path('products/<slug:category_slug>/', views.product_list, name="product_list_by_category"),
    path('products/detail/<slug:slug>/', views.product_detail, name="product_detail"),
    path('rate/<int:product_id>/', views.rate_product, name="rate_product"),
    
    # cart related urls
    path('cart/', views.cart_detail, name="cart_detail"),
    path('cart/add/<int:product_id>/', views.cart_add, name="cart_add"),
    path('cart/remove/<int:product_id>/', views.cart_remove, name="cart_remove"),
    path('cart/update/<int:product_id>/', views.cart_update, name="cart_update"),
    
    # checkout related urls
    path('checkout/', views.checkout, name="checkout"),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name="cancel_order"),
    
    # profile
     path('profile/', views.profile, name="profile"),
]
