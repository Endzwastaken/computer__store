from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'phone', 'date_joined']
    list_filter = ['is_staff', 'is_superuser', 'is_active']
    search_fields = ['username', 'email', 'phone']

    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительная информация', {
            'fields': ('phone', 'address', 'birth_date'),
        }),
    )