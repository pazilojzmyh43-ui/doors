from django.contrib import admin

from .models import Cart, CartItem, Category, News, Order, OrderItem, Product, Profile, WorkVideo


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'position')
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'in_stock')
    list_filter = ('category', 'in_stock')
    search_fields = ('name', 'description')


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'published_at')
    search_fields = ('title',)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone')
    list_filter = ('role',)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total', 'created_at')
    list_filter = ('status',)
    inlines = [OrderItemInline]


@admin.register(WorkVideo)
class WorkVideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'place', 'shot_at')


admin.site.register(Cart)
admin.site.register(CartItem)
