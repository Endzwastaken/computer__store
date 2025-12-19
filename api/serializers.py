"""
Сериализаторы для API.
"""

from rest_framework import serializers
from products.models import Category, Manufacturer, Product, ProductImage, Specification
from orders.models import Order, OrderItem, Cart, CartItem
from users.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'address', 'first_name', 'last_name')
        read_only_fields = ('id',)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ManufacturerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Manufacturer
        fields = '__all__'


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'image', 'alt_text', 'is_main')


class SpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specification
        fields = ('name', 'value')


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    manufacturer = ManufacturerSerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    specifications = SpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ('id', 'product', 'quantity', 'total_price')

    def get_total_price(self, obj):
        return obj.total_price


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total_price', 'created_at', 'updated_at')

    def get_total_price(self, obj):
        return obj.total_price


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ('id', 'product', 'quantity', 'price', 'total_price')

    def get_total_price(self, obj):
        return obj.total_price


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user = UserSerializer(read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ('order_number', 'user', 'total_price', 'created_at', 'updated_at')