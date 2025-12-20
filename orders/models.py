"""
Модели для заказов и корзины с поддержкой транзакций.
"""

from django.db import models
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError


class Order(models.Model):
    """Заказ."""
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('processing', 'В сборке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]

    PAYMENT_METHOD_CHOICES = [
        ('card', 'Карта онлайн'),
        ('cash', 'Наличные'),
        ('bank_transfer', 'Банковский перевод'),
    ]

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='orders'
    )
    order_number = models.CharField('Номер заказа', max_length=20, unique=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_method = models.CharField('Способ оплаты', max_length=20, choices=PAYMENT_METHOD_CHOICES)
    total_price = models.DecimalField('Общая сумма', max_digits=12, decimal_places=2)
    shipping_address = models.TextField('Адрес доставки')
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email')
    comment = models.TextField('Комментарий', blank=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_number']),
            models.Index(fields=['status']),
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            self.order_number = f'ORD-{timestamp}-{self.user.id}'
        super().save(*args, **kwargs)

    @transaction.atomic
    def process_order(self):
        """Обработка заказа с блокировками."""
        for order_item in self.items.select_for_update().all():
            product = order_item.product

            locked_product = type(product).objects.select_for_update().get(pk=product.pk)

            if order_item.quantity > locked_product.quantity:
                raise ValueError(
                    f"Недостаточно товара '{product.name}'. "
                    f"Доступно: {locked_product.quantity}, "
                    f"требуется: {order_item.quantity}"
                )

            locked_product.quantity = models.F('quantity') - order_item.quantity
            locked_product.save(update_fields=['quantity'])

        self.status = 'processing'
        self.save(update_fields=['status'])
        return True


class OrderItem(models.Model):
    """Элемент заказа."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    quantity = models.IntegerField('Количество')
    price = models.DecimalField('Цена за единицу', max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        return self.price * self.quantity


class Cart(models.Model):
    """Корзина покупок."""
    user = models.OneToOneField(
        'users.User',
        on_delete=models.CASCADE,
        related_name='cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        return f'Корзина пользователя {self.user.username}'

    @property
    def total_price(self):
        """Общая стоимость товаров в корзине."""
        return sum(item.total_price for item in self.items.all())

    @transaction.atomic
    def checkout(self):
        """Оформление заказа из корзины с блокировками."""
        for cart_item in self.items.select_for_update().all():
            product = cart_item.product

            locked_product = type(product).objects.select_for_update().get(pk=product.pk)

            if cart_item.quantity > locked_product.quantity:
                raise ValueError(
                    f'Недостаточно товара: {locked_product.name}. '
                    f'Доступно: {locked_product.quantity}'
                )

        order = Order.objects.create(
            user=self.user,
            payment_method='card',
            total_price=self.total_price,
            shipping_address=self.user.address or '',
            phone=self.user.phone or '',
            email=self.user.email,
            comment='Заказ из корзины'
        )

        for cart_item in self.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )

            cart_item.product.quantity -= cart_item.quantity
            cart_item.product.save()

        self.items.all().delete()
        return order


class CartItem(models.Model):
    """Элемент корзины."""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        'products.Product',
        on_delete=models.CASCADE,
        verbose_name='Товар'
    )
    quantity = models.IntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Элемент корзины'
        verbose_name_plural = 'Элементы корзины'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def clean(self):
        if self.quantity > self.product.quantity:
            raise ValidationError(
                f'Недостаточно товара "{self.product.name}". '
                f'Доступно: {self.product.quantity}'
            )