"""
ViewSets для API с поддержкой транзакций.
"""

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db import transaction

from products.models import Category, Manufacturer, Product
from orders.models import Order, Cart, CartItem
from users.models import User
from .serializers import *


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорий."""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ManufacturerViewSet(viewsets.ModelViewSet):
    """ViewSet для производителей."""
    queryset = Manufacturer.objects.all()
    serializer_class = ManufacturerSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ProductViewSet(viewsets.ModelViewSet):
    """ViewSet для товаров."""
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['category', 'manufacturer']

    def get_queryset(self):
        queryset = Product.objects.all()

        min_price = self.request.query_params.get('min_price')
        max_price = self.request.query_params.get('max_price')

        if min_price:
            queryset = queryset.filter(price__gte=min_price)
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        search = self.request.query_params.get('search')
        if search:
            from django.db.models import Q
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def add_to_cart(self, request, pk=None):
        """Добавить товар в корзину через API."""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Требуется авторизация'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        product = self.get_object()
        quantity = int(request.data.get('quantity', 1))

        if quantity > product.quantity:
            return Response(
                {'error': f'Недостаточно товара. Доступно: {product.quantity}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data)


class CartViewSet(viewsets.ModelViewSet):
    """ViewSet для корзины."""
    serializer_class = CartSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Cart.objects.filter(user=self.request.user)

    def get_object(self):
        cart, created = Cart.objects.get_or_create(user=self.request.user)
        return cart

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def add_item(self, request):
        """Добавить товар в корзину."""
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity', 1))

        product = get_object_or_404(Product, id=product_id)

        if quantity > product.quantity:
            return Response(
                {'error': f'Недостаточно товара. Доступно: {product.quantity}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        serializer = CartSerializer(cart)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def remove_item(self, request):
        """Удалить товар из корзины."""
        item_id = request.data.get('item_id')

        cart = get_object_or_404(Cart, user=request.user)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()

        serializer = CartSerializer(cart)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet для заказов."""
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).order_by('-created_at')

    @transaction.atomic
    def create(self, request):
        """Создать заказ из корзины."""
        cart = Cart.objects.filter(user=request.user).first()

        if not cart or not cart.items.exists():
            return Response(
                {'error': 'Корзина пуста'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            for item in cart.items.all():
                if item.quantity > item.product.quantity:
                    raise ValueError(
                        f'Недостаточно товара: {item.product.name}'
                    )

            order = Order.objects.create(
                user=request.user,
                payment_method=request.data.get('payment_method', 'card'),
                total_price=cart.total_price,
                shipping_address=request.data.get('shipping_address', ''),
                phone=request.data.get('phone', request.user.phone or ''),
                email=request.data.get('email', request.user.email),
                comment=request.data.get('comment', '')
            )

            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )

                item.product.quantity -= item.quantity
                item.product.save()

            cart.items.all().delete()

            serializer = OrderSerializer(order)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )


class UserRegistrationView(viewsets.GenericViewSet):
    """Регистрация пользователя через API."""
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        password = request.data.get('password')
        user = serializer.save()
        user.set_password(password)
        user.save()

        token, created = Token.objects.get_or_create(user=user)

        Cart.objects.create(user=user)

        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)