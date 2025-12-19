"""
Утилиты для работы с транзакциями и уровнями изоляции.
"""

from django.db import transaction
from django.db import connection
import logging

logger = logging.getLogger(__name__)


class TransactionManager:
    """Менеджер для управления транзакциями."""

    @staticmethod
    def set_read_uncommitted():
        """Устанавливает уровень изоляции READ UNCOMMITTED."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED;")
        except Exception as e:
            logger.error(f"Ошибка установки уровня изоляции: {e}")

    @staticmethod
    def execute_in_read_uncommitted(func, *args, **kwargs):
        """Выполняет функцию в транзакции с READ UNCOMMITTED."""
        try:
            TransactionManager.set_read_uncommitted()

            with transaction.atomic():
                result = func(*args, **kwargs)
                return result

        except Exception as e:
            logger.error(f"Ошибка в транзакции: {e}")
            raise


def read_uncommitted_transaction(func):
    """Декоратор для выполнения функций в транзакции READ UNCOMMITTED."""

    def wrapper(*args, **kwargs):
        return TransactionManager.execute_in_read_uncommitted(func, *args, **kwargs)

    return wrapper