"""
Модели для пользователей.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Расширенная модель пользователя."""
    phone = models.CharField('Телефон', max_length=20, blank=True)
    address = models.TextField('Адрес', blank=True)
    birth_date = models.DateField('Дата рождения', null=True, blank=True)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        return self.username