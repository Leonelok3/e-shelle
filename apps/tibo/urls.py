from django.urls import path

from apps.tibo import views

app_name = "tibo"

urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("shop/", views.ShopView.as_view(), name="shop"),
    path("search/", views.SearchView.as_view(), name="search"),
    path("category/<slug:slug>/", views.CategoryView.as_view(), name="category"),
    path("product/<slug:slug>/", views.ProductDetailView.as_view(), name="product_detail"),
    path("cart/", views.CartView.as_view(), name="cart"),
    path("cart/add/", views.add_to_cart, name="add_to_cart"),
    path("cart/item/<uuid:item_id>/", views.update_cart_item, name="update_cart_item"),
    path("cart/coupon/", views.apply_coupon, name="apply_coupon"),
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    path("login/", views.LoginView.as_view(), name="login"),
    path("register/", views.RegisterView.as_view(), name="register"),
    path("account/", views.AccountDashboardView.as_view(), name="account_dashboard"),
    path("orders/", views.OrdersView.as_view(), name="orders"),
    path("wishlist/", views.WishlistView.as_view(), name="wishlist"),
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("about/", views.AboutView.as_view(), name="about"),
    path("contact/", views.ContactView.as_view(), name="contact"),
    path("faq/", views.FAQView.as_view(), name="faq"),
    path("privacy/", views.PrivacyView.as_view(), name="privacy"),
    path("terms/", views.TermsView.as_view(), name="terms"),
]
