from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView, TemplateView

from apps.tibo.forms import CheckoutForm
from apps.tibo.models import Category, Order, Product, Wishlist
from apps.tibo.repositories import get_or_create_cart
from apps.tibo.selectors import product_detail, product_list, trending_products
from apps.tibo.services.cart_service import CartService
from apps.tibo.services.order_service import OrderService
from apps.tibo.services.payment_service import PaymentService


class HomeView(TemplateView):
    template_name = "tibo/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["featured_products"] = Product.objects.published().filter(is_featured=True).prefetch_related("images")[:8]
        ctx["trending_products"] = trending_products(8)
        ctx["categories"] = Category.objects.published().filter(is_featured=True)[:6]
        return ctx


class ShopView(ListView):
    template_name = "tibo/shop.html"
    context_object_name = "products"
    paginate_by = 24

    def get_queryset(self):
        return product_list(
            query=self.request.GET.get("q"),
            category_slug=self.request.GET.get("category"),
            min_price=self.request.GET.get("min_price"),
            max_price=self.request.GET.get("max_price"),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.published()
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class CategoryView(ShopView):
    def get_queryset(self):
        self.category = get_object_or_404(Category.objects.published(), slug=self.kwargs["slug"])
        return product_list(category_slug=self.category.slug, query=self.request.GET.get("q"))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["category"] = self.category
        return ctx


class SearchView(ShopView):
    template_name = "tibo/search.html"


class ProductDetailView(DetailView):
    template_name = "tibo/product_detail.html"
    context_object_name = "product"

    def get_object(self):
        return product_detail(self.kwargs["slug"])

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["related_products"] = (
            Product.objects.published()
            .filter(category=self.object.category)
            .exclude(id=self.object.id)
            .prefetch_related("images")[:4]
        )
        return ctx


class CartView(TemplateView):
    template_name = "tibo/cart.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cart"] = get_or_create_cart(self.request)
        return ctx


@require_POST
def add_to_cart(request):
    cart = CartService.add(
        request,
        product_id=request.POST.get("product_id"),
        variant_id=request.POST.get("variant_id") or None,
        quantity=request.POST.get("quantity", 1),
    )
    if request.headers.get("HX-Request"):
        return render(request, "tibo/partials/cart_drawer.html", {"cart": cart})
    return redirect("tibo:cart")


@require_POST
def update_cart_item(request, item_id):
    cart = get_or_create_cart(request)
    CartService.update_item(cart, item_id, request.POST.get("quantity", 1))
    if request.headers.get("HX-Request"):
        return render(request, "tibo/partials/cart_summary.html", {"cart": cart})
    return redirect("tibo:cart")


@require_POST
def apply_coupon(request):
    cart = get_or_create_cart(request)
    if CartService.apply_coupon(cart, request.POST.get("code", "")):
        messages.success(request, "Coupon appliqué.")
    else:
        messages.error(request, "Coupon invalide ou expiré.")
    return redirect("tibo:cart")


class CheckoutView(TemplateView):
    template_name = "tibo/checkout.html"

    def get(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        return render(request, self.template_name, {"cart": cart, "form": CheckoutForm()})

    def post(self, request, *args, **kwargs):
        cart = get_or_create_cart(request)
        form = CheckoutForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"cart": cart, "form": form})
        order = OrderService.create_from_cart(
            cart=cart,
            email=form.cleaned_data["email"],
            shipping_address=form.address_payload(),
            user=request.user if request.user.is_authenticated else None,
        )
        if form.cleaned_data["payment_provider"] == "paypal":
            PaymentService.create_paypal_order(order)
            messages.success(request, "Commande créée. Paiement PayPal prêt à connecter.")
            return redirect("tibo:orders")
        try:
            session = PaymentService.create_stripe_checkout(
                order,
                request.build_absolute_uri(reverse("tibo:orders")),
                request.build_absolute_uri(reverse("tibo:cart")),
            )
            return redirect(session.url)
        except RuntimeError as exc:
            messages.warning(request, str(exc))
            return redirect("tibo:orders")


class AccountDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "tibo/account_dashboard.html"


class OrdersView(LoginRequiredMixin, ListView):
    template_name = "tibo/orders.html"
    context_object_name = "orders"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")


class WishlistView(LoginRequiredMixin, ListView):
    template_name = "tibo/wishlist.html"
    context_object_name = "wishlist_items"

    def get_queryset(self):
        return Wishlist.objects.filter(user=self.request.user).select_related("product").prefetch_related("product__images")


class AboutView(TemplateView):
    template_name = "tibo/about.html"


class ContactView(TemplateView):
    template_name = "tibo/contact.html"


class FAQView(TemplateView):
    template_name = "tibo/faq.html"


class PrivacyView(TemplateView):
    template_name = "tibo/privacy.html"


class TermsView(TemplateView):
    template_name = "tibo/terms.html"


class LoginView(TemplateView):
    template_name = "tibo/login.html"


class RegisterView(TemplateView):
    template_name = "tibo/register.html"


@staff_member_required
def admin_dashboard(request):
    orders = Order.objects.all()
    ctx = {
        "revenue": orders.aggregate(total=Sum("total"))["total"] or 0,
        "orders_count": orders.count(),
        "products_count": Product.objects.count(),
        "top_products": Product.objects.annotate(order_count=Count("orderitem")).order_by("-order_count")[:5],
        "recent_orders": orders[:8],
    }
    return render(request, "tibo/admin_dashboard.html", ctx)
