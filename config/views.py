"""
Основные представления (HTML) проекта.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q

from products.models import Product, Category
from orders.models import Cart, CartItem, Order
from users.models import User


def home(request):
    """Главная страница."""
    # Получаем категории с количеством товаров
    from django.db.models import Count  # Добавьте этот импорт в начале файла

    categories = Category.objects.annotate(
        product_count=Count('products')
    ).order_by('-product_count')[:4]  # Берем 4 самые популярные

    # Получаем популярные товары (первые 8)
    products = Product.objects.filter(quantity__gt=0)[:8]

    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'home.html', context)


def products_list(request):
    """Каталог товаров."""
    products = Product.objects.all()
    categories = Category.objects.all()

    category_id = request.GET.get('category')
    if category_id:
        products = products.filter(category_id=category_id)

    search = request.GET.get('search')
    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )

    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)

    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'products/list.html', context)


def product_detail(request, product_id):
    """Детальная страница товара."""
    product = get_object_or_404(Product, id=product_id)

    context = {
        'product': product,
    }
    return render(request, 'products/detail.html', context)


@login_required
def order_detail_view(request, order_id):
    """Детальная страница заказа."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    context = {
        'order': order,
    }
    return render(request, 'users/order_detail.html', context)


@login_required
def add_to_cart(request, product_id):
    """Добавление товара в корзину."""
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        quantity = int(request.POST.get('quantity', 1))

        if quantity > product.quantity:
            messages.error(request,
                f'Недостаточно товара. Доступно: {product.quantity}')
            return redirect('product_detail', product_id=product_id)

        cart, created = Cart.objects.get_or_create(user=request.user)

        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        messages.success(request, f'Товар "{product.name}" добавлен в корзину')

    return redirect(request.META.get('HTTP_REFERER', 'home'))


@login_required
def cart_view(request):
    """
    Страница корзины.
    """
    cart = Cart.objects.filter(user=request.user).first()

    if not cart:
        cart = Cart.objects.create(user=request.user)

    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        action = request.POST.get('action')

        if action == 'clear':
            # Очищаем всю корзину
            cart.items.all().delete()
            messages.success(request, 'Корзина очищена')
            return redirect('cart')

        elif item_id and action:
            cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

            if action == 'remove':
                cart_item.delete()
                messages.success(request, 'Товар удален из корзины')
            elif action == 'update':
                quantity = int(request.POST.get('quantity', 1))
                if quantity > 0:
                    if quantity > cart_item.product.quantity:
                        messages.error(request,
                                       f'Недостаточно товара. Доступно: {cart_item.product.quantity}')
                    else:
                        cart_item.quantity = quantity
                        cart_item.save()
                        messages.success(request, 'Количество обновлено')
                else:
                    cart_item.delete()
                    messages.success(request, 'Товар удален из корзины')

        return redirect('cart')

    context = {
        'cart': cart,
    }
    return render(request, 'orders/cart.html', context)


@login_required
def checkout_view(request):
    """Оформление заказа."""
    cart = Cart.objects.filter(user=request.user).first()

    if not cart or not cart.items.exists():
        messages.warning(request, 'Ваша корзина пуста')
        return redirect('cart')

    if request.method == 'POST':
        try:
            order = Order.objects.create(
                user=request.user,
                payment_method=request.POST.get('payment_method', 'card'),
                total_price=cart.total_price,
                shipping_address=request.POST.get('shipping_address', ''),
                phone=request.POST.get('phone', request.user.phone or ''),
                email=request.POST.get('email', request.user.email),
                comment=request.POST.get('comment', '')
            )

            for cart_item in cart.items.all():
                order.items.create(
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )

                cart_item.product.quantity -= cart_item.quantity
                cart_item.product.save()

            cart.items.all().delete()

            messages.success(request, f'Заказ #{order.order_number} успешно оформлен!')
            return redirect('order_success', order_number=order.order_number)

        except Exception as e:
            messages.error(request, f'Ошибка при оформлении заказа: {str(e)}')

    context = {
        'cart': cart,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
def order_success_view(request, order_number):
    """Успешное оформление заказа."""
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    context = {
        'order': order,
    }
    return render(request, 'orders/success.html', context)


@login_required
def profile_view(request):
    """Профиль пользователя."""
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.phone = request.POST.get('phone', '')
        user.address = request.POST.get('address', '')
        user.save()

        messages.success(request, 'Профиль успешно обновлен!')

    return render(request, 'users/profile.html')


@login_required
def orders_list(request):
    """Список заказов."""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'orders': orders,
    }
    return render(request, 'users/orders.html', context)


def login_view(request):
    """Вход в систему."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user.username}!')

            next_page = request.GET.get('next', 'home')
            return redirect(next_page)
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')

    return render(request, 'users/login.html')


def register_view(request):
    """Регистрация."""
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')

        if password != password2:
            messages.error(request, 'Пароли не совпадают.')
            return render(request, 'users/register.html')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует.')
            return render(request, 'users/register.html')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            phone=request.POST.get('phone', ''),
            address=request.POST.get('address', '')
        )

        Cart.objects.create(user=user)

        login(request, user)
        messages.success(request, f'Регистрация успешна! Добро пожаловать, {username}!')
        return redirect('home')

    return render(request, 'users/register.html')


def logout_view(request):
    """Выход из системы."""
    logout(request)
    messages.info(request, 'Вы успешно вышли из системы.')
    return redirect('home')