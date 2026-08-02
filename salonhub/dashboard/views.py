import datetime as dt

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from salonhub.bookings.models import Appointment
from salonhub.salons.models import Salon, Service, OpeningHour
from .forms import SalonForm, ServiceForm


@login_required
def home(request):
    if not request.user.is_owner:
        return render(request, "dashboard/not_owner.html")

    salons = Salon.objects.filter(owner=request.user)
    today = dt.date.today()
    appointments = Appointment.objects.filter(salon__owner=request.user).select_related("salon", "service")

    stats = {
        "total_salons": salons.count(),
        "today_count": appointments.filter(date=today).count(),
        "pending_count": appointments.filter(status=Appointment.Status.PENDING).count(),
        "week_count": appointments.filter(
            date__range=[today, today + dt.timedelta(days=7)]
        ).count(),
    }

    return render(request, "dashboard/home.html", {
        "salons": salons,
        "appointments": appointments[:30],
        "stats": stats,
    })


@login_required
def salon_create(request):
    if not request.user.is_owner:
        return render(request, "dashboard/not_owner.html")

    if request.method == "POST":
        form = SalonForm(request.POST, request.FILES)
        if form.is_valid():
            salon = form.save(commit=False)
            salon.owner = request.user
            salon.save()

            # Initialize default opening hours for each day of the week
            for day in range(7):
                OpeningHour.objects.get_or_create(
                    salon=salon,
                    weekday=day,
                    defaults={
                        "start_time": dt.time(8, 0),
                        "end_time": dt.time(18, 0),
                        "is_closed": False,
                    }
                )

            messages.success(request, f"L'établissement \"{salon.name}\" a été créé avec succès !")
            return redirect("dashboard:salon_services", salon_id=salon.id)
    else:
        form = SalonForm()

    return render(request, "dashboard/salon_form.html", {
        "form": form,
        "title": "Ajouter un établissement",
    })


@login_required
def salon_edit(request, pk):
    if not request.user.is_owner:
        return render(request, "dashboard/not_owner.html")

    salon = get_object_or_404(Salon, pk=pk, owner=request.user)

    if request.method == "POST":
        form = SalonForm(request.POST, request.FILES, instance=salon)
        if form.is_valid():
            form.save()
            messages.success(request, f"L'établissement \"{salon.name}\" a été mis à jour.")
            return redirect("dashboard:home")
    else:
        form = SalonForm(instance=salon)

    return render(request, "dashboard/salon_form.html", {
        "form": form,
        "salon": salon,
        "title": f"Modifier {salon.name}",
    })


@login_required
def salon_services(request, salon_id):
    if not request.user.is_owner:
        return render(request, "dashboard/not_owner.html")

    salon = get_object_or_404(Salon, pk=salon_id, owner=request.user)
    services = salon.services.all()

    if request.method == "POST":
        form = ServiceForm(request.POST)
        if form.is_valid():
            service = form.save(commit=False)
            service.salon = salon
            service.save()
            messages.success(request, f"La prestation \"{service.name}\" a été ajoutée.")
            return redirect("dashboard:salon_services", salon_id=salon.id)
    else:
        form = ServiceForm()

    return render(request, "dashboard/services.html", {
        "salon": salon,
        "services": services,
        "form": form,
    })


@login_required
def service_delete(request, pk):
    if not request.user.is_owner:
        return render(request, "dashboard/not_owner.html")

    service = get_object_or_404(Service, pk=pk, salon__owner=request.user)
    salon_id = service.salon.id
    name = service.name
    service.delete()
    messages.success(request, f"La prestation \"{name}\" a été supprimée.")
    return redirect("dashboard:salon_services", salon_id=salon_id)


@login_required
@require_POST
def update_appointment_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, salon__owner=request.user)
    new_status = request.POST.get("status")
    if new_status in dict(Appointment.Status.choices):
        appointment.status = new_status
        appointment.save(update_fields=["status"])
        messages.success(request, "Statut du rendez-vous mis à jour.")
    return redirect("dashboard:home")
