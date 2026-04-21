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
    path('payment/sslcommerz/success/', views.sslcommerz_success, name='sslcommerz_success'),
    path('payment/sslcommerz/fail/', views.sslcommerz_fail, name='sslcommerz_fail'),
    path('payment/sslcommerz/cancel/', views.sslcommerz_cancel, name='sslcommerz_cancel'),
    path('payment/sslcommerz/ipn/', views.sslcommerz_ipn, name='sslcommerz_ipn'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name="cancel_order"),
    
    # profile
    path('profile/', views.profile, name="profile"),

    # frontend admin panel
    path('store-admin/', views.frontend_admin_dashboard, name='frontend_admin_dashboard'),
    path('store-admin/orders/<int:order_id>/status/', views.frontend_admin_update_order_status, name='frontend_admin_update_order_status'),
    path('store-admin/products/add/', views.frontend_admin_add_product, name='frontend_admin_add_product'),
    path('store-admin/products/<int:product_id>/update/', views.frontend_admin_update_product, name='frontend_admin_update_product'),
    path('store-admin/products/<int:product_id>/remove/', views.frontend_admin_remove_product, name='frontend_admin_remove_product'),
]
