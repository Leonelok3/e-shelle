from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.tibo.api.views import CartViewSet, CategoryViewSet, OrderViewSet, ProductViewSet, WishlistViewSet

app_name = "tibo_api"

router = DefaultRouter()
router.register("products", ProductViewSet, basename="product")
router.register("categories", CategoryViewSet, basename="category")
router.register("cart", CartViewSet, basename="cart")
router.register("orders", OrderViewSet, basename="order")
router.register("wishlist", WishlistViewSet, basename="wishlist")

urlpatterns = [path("", include(router.urls))]

