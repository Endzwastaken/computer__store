"""
URL маршруты для API.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken.views import obtain_auth_token
from .views import (
    CategoryViewSet, ManufacturerViewSet, ProductViewSet,
    CartViewSet, OrderViewSet, UserRegistrationView
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'manufacturers', ManufacturerViewSet)
router.register(r'products', ProductViewSet)
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/register/', UserRegistrationView.as_view({'post': 'create'}), name='api-register'),
    path('auth/login/', obtain_auth_token, name='api-login'),
]