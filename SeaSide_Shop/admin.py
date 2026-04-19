from django.contrib import admin
from . import models 
# Register your models here.

@admin.register(models.Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug' : ('name',)}
    

@admin.register(models.Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'price', 'stock', 'available', 'created_at', 'updated_at']
    prepopulated_fields = {'slug' : ('name', )}
    
@admin.register(models.Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'payment_method', 'payment_status', 'product_fee', 'shipping_fee', 'status', 'paid', 'created_at']
    list_filter = ['status', 'paid', 'payment_method', 'payment_status', 'created_at']
    search_fields = ['id', 'user__username', 'email', 'phone']
    list_editable = ['status', 'paid', 'payment_status']

    @admin.display(description='Product Fee')
    def product_fee(self, obj):
        return obj.get_items_total()


admin.site.register(models.Rating)
admin.site.register(models.Cart)
admin.site.register(models.CartItem)
admin.site.register(models.OrderItem)
