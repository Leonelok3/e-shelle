"""
E-Shelle Resto — Views
Restaurant discovery platform for Cameroon.
"""
import json
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, FormView

from .forms import (
    DishAvailabilityForm, DishForm, MenuCategoryForm,
    RestaurantForm, RestaurantRegisterForm, ReviewForm,
)
from .models import (
    City, ContactLog, Dish, Favorite, FoodCategory,
    HeroBanner, MenuCategory, Neighborhood, Notification, Restaurant,
    Review, Subscription,
)

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _is_staff(user):
    return user.is_staff


# ──────────────────────────────────────────────────────────────────────────────
# Public Views
# ──────────────────────────────────────────────────────────────────────────────

class HomeView(TemplateView):
    """Page d'accueil E-Shelle Resto."""
    template_name = "resto/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        approved_qs = Restaurant.objects.visible().select_related("city", "neighborhood")

        ctx["featured_restaurants"] = (
            approved_qs.filter(is_featured=True)
            .prefetch_related("categories")
            .order_by("-views_count")[:8]
        )
        ctx["open_now"] = (
            approved_qs.filter(status="open")
            .prefetch_related("categories")
            .order_by("?")[:6]
        )
        visible_restaurants = Restaurant.objects.visible()
        ctx["popular_dishes"] = (
            Dish.objects.filter(
                is_popular=True, is_active=True,
                restaurant__in=visible_restaurants,
            )
            .select_related("restaurant", "restaurant__city")
            .order_by("?")[:8]
        )
        ctx["affordable_dishes"] = (
            Dish.objects.filter(
                price__lte=1500, is_active=True,
                restaurant__in=visible_restaurants,
            )
            .select_related("restaurant", "restaurant__city")
            .order_by("?")[:6]
        )
        ctx["food_categories"] = FoodCategory.objects.all().order_by("order")
        ctx["cities"] = City.objects.filter(is_active=True)
        ctx["hero_banners"] = HeroBanner.objects.filter(
            is_active=True
        ).select_related("restaurant").order_by("order")
        return ctx


class RestaurantListView(View):
    """Liste des restaurants avec filtres HTMX."""
    template_name = "resto/restaurant_list.html"
    partial_template = "resto/partials/restaurant_grid.html"
    per_page = 12

    def get(self, request, *args, **kwargs):
        qs = (
            Restaurant.objects.visible()
            .select_related("city", "neighborhood")
            .prefetch_related("categories")
        )

        city_slug = request.GET.get("city", "").strip()
        neighborhood_slug = request.GET.get("neighborhood", "").strip()
        category_slug = request.GET.get("category", "").strip()
        status = request.GET.get("status", "").strip()
        q = request.GET.get("q", "").strip()

        if city_slug:
            qs = qs.filter(city__slug=city_slug)
        if neighborhood_slug:
            qs = qs.filter(neighborhood__slug=neighborhood_slug)
        if category_slug:
            qs = qs.filter(categories__slug=category_slug)
        if status in ("open", "closed", "opening_soon"):
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(
                Q(name__icontains=q) |
                Q(description__icontains=q) |
                Q(address__icontains=q)
            )

        qs = qs.distinct().order_by("-is_featured", "-views_count", "name")
        paginator = Paginator(qs, self.per_page)
        page_obj = paginator.get_page(request.GET.get("page", 1))

        ctx = {
            "page_obj": page_obj,
            "restaurants": page_obj.object_list,
            "cities": City.objects.filter(is_active=True),
            "food_categories": FoodCategory.objects.all().order_by("order"),
            "active_city": city_slug,
            "active_category": category_slug,
            "active_status": status,
            "q": q,
            "statuses": [
                ("open", "Ouvert"),
                ("closed", "Fermé"),
                ("opening_soon", "Bientôt ouvert"),
            ],
        }

        # HTMX partial response
        if request.headers.get("HX-Request"):
            return render(request, self.partial_template, ctx)
        return render(request, self.template_name, ctx)


class RestaurantDetailView(View):
    """Page de détail d'un restaurant."""
    template_name = "resto/restaurant_detail.html"

    def get(self, request, slug, *args, **kwargs):
        qs = (
            Restaurant.objects.select_related("city", "neighborhood")
            .prefetch_related("categories", "menu_categories__dishes")
        )
        # Le propriétaire peut voir sa propre page même avant approbation
        is_owner = (
            request.user.is_authenticated and
            qs.filter(slug=slug, owner=request.user, is_active=True).exists()
        )
        if is_owner:
            restaurant = get_object_or_404(qs, slug=slug, is_active=True)
        else:
            restaurant = get_object_or_404(qs.visible(), slug=slug)

        is_preview = is_owner and not Restaurant.objects.visible().filter(pk=restaurant.pk).exists()

        # Increment views once per session
        session_key = f"resto_viewed_{restaurant.pk}"
        if not request.session.get(session_key):
            Restaurant.objects.filter(pk=restaurant.pk).update(
                views_count=restaurant.views_count + 1
            )
            request.session[session_key] = True

        # Menu grouped by category
        menu_categories = (
            MenuCategory.objects.filter(restaurant=restaurant)
            .prefetch_related(
                "dishes"
            )
            .order_by("order", "name")
        )
        # Dishes without category
        uncategorized = restaurant.dishes.filter(
            category__isnull=True, is_active=True
        ).order_by("order", "name")

        # Is favorited by current user?
        is_favorite = False
        if request.user.is_authenticated:
            is_favorite = Favorite.objects.filter(
                user=request.user, restaurant=restaurant
            ).exists()

        # Reviews
        reviews = (
            Review.objects.filter(restaurant=restaurant, is_approved=True)
            .order_by("-created_at")[:20]
        )
        review_stats = restaurant.reviews.filter(is_approved=True).aggregate(
            avg=Avg("rating"), total=Count("id")
        )
        avg_rating = review_stats["avg"] or 0
        review_count = review_stats["total"] or 0

        # Rating distribution 5→1 (for bar chart display)
        rating_dist = []
        for i in range(5, 0, -1):
            rating_dist.append((i, restaurant.reviews.filter(
                is_approved=True, rating=i
            ).count()))

        ctx = {
            "restaurant": restaurant,
            "menu_categories": menu_categories,
            "uncategorized_dishes": uncategorized,
            "is_favorite": is_favorite,
            "contact_count": restaurant.contact_logs.count(),
            "reviews": reviews,
            "avg_rating": avg_rating,
            "review_count": review_count,
            "rating_dist": rating_dist,
            "review_form": ReviewForm(),
            "is_preview": is_preview,
        }
        return render(request, self.template_name, ctx)


class TrackContactView(View):
    """Enregistre un clic contact (HTMX POST)."""

    def post(self, request, *args, **kwargs):
        restaurant_id = request.POST.get("restaurant_id")
        action = request.POST.get("action")
        dish_id = request.POST.get("dish_id")

        if not restaurant_id or action not in ("call", "whatsapp"):
            return HttpResponse(status=400)

        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id, is_active=True)
        except Restaurant.DoesNotExist:
            return HttpResponse(status=404)

        dish = None
        if dish_id:
            try:
                dish = Dish.objects.get(pk=dish_id, restaurant=restaurant)
            except Dish.DoesNotExist:
                pass

        ContactLog.objects.create(
            restaurant=restaurant,
            action=action,
            dish=dish,
            session_key=request.session.session_key or "",
            ip_address=_get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
        )
        return HttpResponse(status=200)


class SearchView(View):
    """Recherche HTMX — retourne un fragment HTML."""
    template_name = "resto/partials/search_results.html"

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "").strip()
        restaurants = []
        dishes = []

        if len(q) >= 2:
            visible_restaurants = Restaurant.objects.visible()
            restaurants = (
                visible_restaurants.filter(
                    Q(name__icontains=q) | Q(description__icontains=q),
                )
                .select_related("city")[:6]
            )
            dishes = (
                Dish.objects.filter(
                    Q(name__icontains=q),
                    is_active=True,
                    restaurant__in=visible_restaurants,
                )
                .select_related("restaurant", "restaurant__city")[:6]
            )

        ctx = {"q": q, "restaurants": restaurants, "dishes": dishes}
        return render(request, self.template_name, ctx)


class ToggleFavoriteView(LoginRequiredMixin, View):
    """Toggle favori restaurant (HTMX POST)."""

    def post(self, request, slug, *args, **kwargs):
        restaurant = get_object_or_404(Restaurant, slug=slug, is_active=True)
        fav, created = Favorite.objects.get_or_create(
            user=request.user, restaurant=restaurant
        )
        if not created:
            fav.delete()
            is_favorite = False
        else:
            is_favorite = True

        return render(request, "resto/partials/favorite_button.html", {
            "restaurant": restaurant,
            "is_favorite": is_favorite,
        })


# ──────────────────────────────────────────────────────────────────────────────
# Dashboard Views (LoginRequired)
# ──────────────────────────────────────────────────────────────────────────────

class DashboardMixin(LoginRequiredMixin):
    """Mixin commun aux vues dashboard — vérifie que l'utilisateur possède un restaurant."""

    def dispatch(self, request, *args, **kwargs):
        # 1. Vérifier l'authentification (LoginRequiredMixin)
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        # 2. Vérifier que l'utilisateur possède un restaurant actif
        if not Restaurant.objects.filter(owner=request.user, is_active=True).exists():
            messages.info(
                request,
                "Vous n'avez pas encore de restaurant enregistré. Créez-le ici."
            )
            return redirect("resto:register")
        # 3. Tout est bon → continuer normalement
        return super().dispatch(request, *args, **kwargs)

    def get_restaurant(self, request):
        return (
            Restaurant.objects
            .select_related("city", "neighborhood", "subscription")
            .get(owner=request.user, is_active=True)
        )


class DashboardHomeView(DashboardMixin, View):
    """Tableau de bord principal du restaurateur."""
    template_name = "resto/dashboard/home.html"

    def get(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        today = timezone.now().date()

        today_views = ContactLog.objects.filter(
            restaurant=restaurant,
            created_at__date=today,
        ).count()
        today_whatsapp = ContactLog.objects.filter(
            restaurant=restaurant,
            created_at__date=today,
            action="whatsapp",
        ).count()
        today_calls = ContactLog.objects.filter(
            restaurant=restaurant,
            created_at__date=today,
            action="call",
        ).count()

        recent_logs = (
            ContactLog.objects.filter(restaurant=restaurant)
            .select_related("dish")
            .order_by("-created_at")[:10]
        )

        ctx = {
            "restaurant": restaurant,
            "today_views": restaurant.views_count,
            "today_contacts": today_views,
            "today_whatsapp": today_whatsapp,
            "today_calls": today_calls,
            "recent_logs": recent_logs,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        """Quick status toggle."""
        restaurant = self.get_restaurant(request)
        new_status = request.POST.get("status")
        if new_status in ("open", "closed", "opening_soon"):
            restaurant.status = new_status
            restaurant.save(update_fields=["status", "updated_at"])
            if request.headers.get("HX-Request"):
                return render(request, "resto/partials/status_badge.html", {
                    "restaurant": restaurant
                })
        return redirect("resto:dashboard_home")


class DashboardProfileView(DashboardMixin, View):
    """Édition du profil du restaurant."""
    template_name = "resto/dashboard/profile.html"

    def get(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        form = RestaurantForm(instance=restaurant)
        return render(request, self.template_name, {"restaurant": restaurant, "form": form})

    def post(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        form = RestaurantForm(request.POST, request.FILES, instance=restaurant)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect("resto:dashboard_profile")
        return render(request, self.template_name, {"restaurant": restaurant, "form": form})


class DashboardMenuView(DashboardMixin, View):
    """Gestion du menu (catégories + plats)."""
    template_name = "resto/dashboard/menu.html"

    def get(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        menu_categories = (
            MenuCategory.objects.filter(restaurant=restaurant)
            .prefetch_related("dishes")
            .order_by("order", "name")
        )
        uncategorized = restaurant.dishes.filter(
            category__isnull=True, is_active=True
        )
        dish_form = DishForm(restaurant=restaurant)
        cat_form = MenuCategoryForm()
        ctx = {
            "restaurant": restaurant,
            "menu_categories": menu_categories,
            "uncategorized": uncategorized,
            "dish_form": dish_form,
            "cat_form": cat_form,
        }
        return render(request, self.template_name, ctx)

    def post(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        action = request.POST.get("action", "")

        if action == "add_category":
            form = MenuCategoryForm(request.POST)
            if form.is_valid():
                cat = form.save(commit=False)
                cat.restaurant = restaurant
                cat.save()
                messages.success(request, "Catégorie ajoutée.")
            else:
                messages.error(request, "Erreur dans le formulaire.")

        elif action == "add_dish":
            form = DishForm(request.POST, request.FILES, restaurant=restaurant)
            if form.is_valid():
                dish = form.save(commit=False)
                dish.restaurant = restaurant
                dish.save()
                messages.success(request, f"Plat « {dish.name} » ajouté.")
            else:
                messages.error(request, "Erreur dans le formulaire du plat.")

        elif action == "delete_category":
            cat_id = request.POST.get("category_id")
            MenuCategory.objects.filter(pk=cat_id, restaurant=restaurant).delete()
            messages.success(request, "Catégorie supprimée.")

        elif action == "delete_dish":
            dish_id = request.POST.get("dish_id")
            Dish.objects.filter(pk=dish_id, restaurant=restaurant).delete()
            messages.success(request, "Plat supprimé.")

        return redirect("resto:dashboard_menu")


class DishAvailabilityToggleView(DashboardMixin, View):
    """Toggle rapide disponibilité plat (HTMX POST)."""

    def post(self, request, pk, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        dish = get_object_or_404(Dish, pk=pk, restaurant=restaurant)

        new_avail = request.POST.get("availability", "available")
        mins = request.POST.get("available_in_minutes")

        if new_avail in ("available", "in_x_minutes", "unavailable"):
            dish.availability = new_avail
            if new_avail == "in_x_minutes" and mins:
                try:
                    dish.available_in_minutes = int(mins)
                except ValueError:
                    pass
            dish.save(update_fields=["availability", "available_in_minutes"])

        if request.headers.get("HX-Request"):
            return render(request, "resto/partials/dish_availability_badge.html", {
                "dish": dish
            })
        return redirect("resto:dashboard_menu")


class DashboardAnalyticsView(DashboardMixin, View):
    """Analytiques — graphiques 7 jours (Chart.js)."""
    template_name = "resto/dashboard/analytics.html"

    def get(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        today = timezone.now().date()

        # Build 7-day arrays
        labels = []
        views_data = []
        whatsapp_data = []
        call_data = []

        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            labels.append(day.strftime("%d/%m"))
            # We approximate daily views from contact logs as proxy
            day_contacts = ContactLog.objects.filter(
                restaurant=restaurant, created_at__date=day
            )
            whatsapp_data.append(day_contacts.filter(action="whatsapp").count())
            call_data.append(day_contacts.filter(action="call").count())
            views_data.append(whatsapp_data[-1] + call_data[-1])

        total_contacts = ContactLog.objects.filter(restaurant=restaurant).count()
        total_whatsapp = ContactLog.objects.filter(restaurant=restaurant, action="whatsapp").count()
        total_calls = ContactLog.objects.filter(restaurant=restaurant, action="call").count()

        ctx = {
            "restaurant": restaurant,
            "chart_labels": json.dumps(labels),
            "chart_views": json.dumps(views_data),
            "chart_whatsapp": json.dumps(whatsapp_data),
            "chart_calls": json.dumps(call_data),
            "total_contacts": total_contacts,
            "total_whatsapp": total_whatsapp,
            "total_calls": total_calls,
        }
        return render(request, self.template_name, ctx)


class RestaurantRegisterView(View):
    """Inscription restaurant — crée le compte utilisateur + restaurant + abonnement."""
    template_name = "resto/register.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Check if user already has a restaurant
            if Restaurant.objects.filter(owner=request.user).exists():
                return redirect("resto:dashboard_home")
        form = RestaurantRegisterForm()
        return render(request, self.template_name, {"form": form})

    def post(self, request, *args, **kwargs):
        form = RestaurantRegisterForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data

            # Create or use existing user
            if request.user.is_authenticated:
                user = request.user
            else:
                # Check email uniqueness
                if User.objects.filter(email=cd["email"]).exists():
                    form.add_error("email", "Un compte avec cet email existe déjà.")
                    return render(request, self.template_name, {"form": form})
                user = User.objects.create_user(
                    username=cd["email"],
                    email=cd["email"],
                    password=cd["password"],
                    first_name=cd["first_name"],
                    last_name=cd["last_name"],
                )

            # Create restaurant (auto-approuvé à la création pendant la phase de lancement)
            restaurant = Restaurant.objects.create(
                owner=user,
                name=cd["restaurant_name"],
                city=cd["city"],
                phone=cd["phone"],
                whatsapp=cd["whatsapp"],
                address=cd["address"],
                opening_time=cd["opening_time"],
                closing_time=cd["closing_time"],
                status="closed",
                is_approved=True,
            )

            # Free trial subscription
            trial_days = getattr(__import__("django.conf", fromlist=["settings"]).settings, "RESTO_FREE_TRIAL_DAYS", 30)
            Subscription.objects.create(
                restaurant=restaurant,
                plan="free_trial",
                expiry_date=date.today() + timedelta(days=trial_days),
            )

            if not request.user.is_authenticated:
                login(request, user)

            messages.success(
                request,
                f"Bienvenue ! Votre restaurant « {restaurant.name} » a été créé. "
                "Votre essai gratuit de 30 jours est activé."
            )
            return redirect("resto:dashboard_home")

        return render(request, self.template_name, {"form": form})


class SubmitReviewView(View):
    """Soumission d'un avis client sur la page restaurant."""

    def post(self, request, slug, *args, **kwargs):
        restaurant = get_object_or_404(
            Restaurant, slug=slug, is_approved=True, is_active=True
        )
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.restaurant = restaurant
            review.save()
            messages.success(
                request,
                "Merci pour votre avis ! Il sera publié après modération (sous 24h)."
            )
        else:
            # Collect errors for flash message
            errors = " ".join(
                e for field_errors in form.errors.values() for e in field_errors
            )
            messages.error(request, f"Veuillez corriger les erreurs : {errors}")
        return redirect("resto:restaurant_detail", slug=slug)


class DashboardNotificationsView(DashboardMixin, View):
    """Liste des notifications du restaurateur."""
    template_name = "resto/dashboard/notifications.html"

    def get(self, request, *args, **kwargs):
        restaurant = self.get_restaurant(request)
        notifications = (
            Notification.objects.filter(restaurant=restaurant)
            .order_by("-created_at")[:60]
        )
        # Mark all unread as read after displaying
        unread_ids = [n.pk for n in notifications if not n.is_read]
        ctx = {
            "restaurant": restaurant,
            "notifications": notifications,
            "unread_count": len(unread_ids),
        }
        if unread_ids:
            Notification.objects.filter(pk__in=unread_ids).update(is_read=True)
        return render(request, self.template_name, ctx)


# ──────────────────────────────────────────────────────────────────────────────
# Admin Panel (staff only)
# ──────────────────────────────────────────────────────────────────────────────

@user_passes_test(_is_staff, login_url="/accounts/login/")
def admin_dashboard(request):
    """Tableau de bord admin personnalisé."""
    today = timezone.now().date()

    restaurants = (
        Restaurant.objects.select_related("city", "owner", "subscription")
        .order_by("-created_at")
    )

    # Handle approve / feature / deactivate actions
    if request.method == "POST":
        action = request.POST.get("action")
        ids = request.POST.getlist("restaurant_ids")
        qs = Restaurant.objects.filter(pk__in=ids)
        if action == "approve":
            qs.update(is_approved=True)
            messages.success(request, f"{qs.count()} restaurant(s) approuvé(s).")
        elif action == "feature":
            qs.update(is_featured=True)
            messages.success(request, f"{qs.count()} restaurant(s) mis en avant.")
        elif action == "deactivate":
            qs.update(is_active=False)
            messages.success(request, f"{qs.count()} restaurant(s) désactivé(s).")
        return redirect("resto:admin_dashboard")

    stats = {
        "total_restaurants": restaurants.count(),
        "pending_approval": restaurants.filter(is_approved=False, is_active=True).count(),
        "active_subscriptions": Subscription.objects.filter(is_active=True, expiry_date__gte=today).count(),
        "contacts_today": ContactLog.objects.filter(created_at__date=today).count(),
    }

    ctx = {
        "restaurants": restaurants[:50],
        "stats": stats,
    }
    return render(request, "resto/admin/dashboard.html", ctx)
