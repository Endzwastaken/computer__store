"""
Контекстные процессоры для проекта.
"""

from orders.models import Cart


def cart_context(request):
    """Добавляет корзину в контекст всех шаблонов."""
    context = {}

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            context['cart'] = cart
            context['cart_items_count'] = cart.items.count()
        else:
            context['cart_items_count'] = 0
    else:
        context['cart_items_count'] = 0

    return context