import datetime as dt

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from salonhub.bookings.models import Appointment
from salonhub.salons.models import Salon


def _owner_required(view):
    return login_required(view)


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
@require_POST
def update_appointment_status(request, pk):
    appointment = get_object_or_404(Appointment, pk=pk, salon__owner=request.user)
    new_status = request.POST.get("status")
    if new_status in dict(Appointment.Status.choices):
        appointment.status = new_status
        appointment.save(update_fields=["status"])
    return redirect("dashboard:home")
