import datetime as dt

from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from salonhub.bookings.forms import AppointmentForm
from .models import Category, Salon


class HomeView(ListView):
    model = Salon
    template_name = "salons/home.html"
    context_object_name = "salons"
    paginate_by = 12

    def get_queryset(self):
        qs = Salon.objects.filter(is_active=True).select_related("category")
        q = self.request.GET.get("q", "").strip()
        city = self.request.GET.get("city", "").strip()
        category = self.request.GET.get("category", "").strip()

        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(district__icontains=q))
        if city:
            qs = qs.filter(city__icontains=city)
        if category:
            qs = qs.filter(category__slug=category)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.all()
        ctx["cities"] = (
            Salon.objects.filter(is_active=True)
            .exclude(city="")
            .order_by("city")
            .values_list("city", flat=True)
            .distinct()
        )
        ctx["q"] = self.request.GET.get("q", "")
        ctx["selected_city"] = self.request.GET.get("city", "")
        ctx["selected_category"] = self.request.GET.get("category", "")
        return ctx


class SalonDetailView(DetailView):
    model = Salon
    template_name = "salons/detail.html"
    context_object_name = "salon"

    def get_queryset(self):
        return Salon.objects.filter(is_active=True).prefetch_related(
            "services", "opening_hours"
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        today = dt.date.today()
        ctx["next_days"] = [today + dt.timedelta(days=i) for i in range(14)]
        ctx["services"] = self.object.services.filter(is_active=True)
        ctx["appointment_form"] = AppointmentForm()
        ctx["opening_hours_ordered"] = self.object.opening_hours.order_by("weekday")
        ctx["today_weekday"] = today.weekday()
        return ctx
