from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Manufacturer, Product, ProductImage, Specification


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'product_count']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Количество товаров'


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ['name', 'country', 'product_count']
    search_fields = ['name', 'country']

    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Количество товаров'


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'manufacturer', 'price', 'quantity', 'available', 'created_at']
    list_filter = ['category', 'manufacturer', 'created_at']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline, SpecificationInline]

    def available(self, obj):
        return obj.quantity > 0
    available.boolean = True
    available.short_description = 'В наличии'