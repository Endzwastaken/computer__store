"""
Модели для товаров с поддержкой транзакций.
"""

from django.db import models
from django.utils.text import slugify
from django.db import transaction
from django.core.exceptions import ValidationError


class Category(models.Model):
    """Категория товаров."""
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Manufacturer(models.Model):
    """Производитель."""
    name = models.CharField(max_length=100, unique=True)
    country = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo = models.ImageField(upload_to='manufacturers/', blank=True, null=True)

    class Meta:
        verbose_name = 'Производитель'
        verbose_name_plural = 'Производители'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар с поддержкой транзакций."""
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('URL', max_length=200, unique=True)
    description = models.TextField('Описание')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Категория'
    )

    manufacturer = models.ForeignKey(
        Manufacturer,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Производитель'
    )

    quantity = models.IntegerField('Количество', default=0)
    warranty = models.IntegerField('Гарантия (мес.)', default=12)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['price']),
            models.Index(fields=['category', 'manufacturer']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def clean(self):
        if self.price < 0:
            raise ValidationError({'price': 'Цена не может быть отрицательной'})
        if self.quantity < 0:
            raise ValidationError({'quantity': 'Количество не может быть отрицательным'})

    @property
    def available(self):
        return self.quantity > 0

    @transaction.atomic
    def reserve(self, quantity):
        """Резервирование товара с блокировкой."""
        if quantity > self.quantity:
            raise ValueError(f"Недостаточно товара. Доступно: {self.quantity}")

        # Блокируем строку для обновления
        product = Product.objects.select_for_update().get(pk=self.pk)
        product.quantity = models.F('quantity') - quantity
        product.save()
        return True


class ProductImage(models.Model):
    """Изображение товара."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=100, blank=True)
    is_main = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'

    def __str__(self):
        return f"Изображение для {self.product.name}"


class Specification(models.Model):
    """Характеристика товара."""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='specifications'
    )
    name = models.CharField('Название', max_length=100)
    value = models.CharField('Значение', max_length=200)

    class Meta:
        verbose_name = 'Характеристика'
        verbose_name_plural = 'Характеристики'

    def __str__(self):
        return f"{self.name}: {self.value}"