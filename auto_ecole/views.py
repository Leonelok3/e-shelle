from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import render, get_object_or_404, redirect

from .forms import DrivingSchoolRegistrationForm
from .models import DrivingSchool, Course

User = get_user_model()


def home(request):
    query = request.GET.get("q", "").strip()
    city = request.GET.get("ville", "").strip()
    schools = (
        DrivingSchool.objects.filter(is_active=True)
        .annotate(course_count=Count("courses", filter=Q(courses__is_published=True)))
        .order_by("-is_featured", "-is_verified", "name")
    )
    if query:
        schools = schools.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(city__icontains=query)
            | Q(address__icontains=query)
        )
    if city:
        schools = schools.filter(city__iexact=city)

    featured_courses = (
        Course.objects.filter(is_published=True, school__is_active=True)
        .select_related("school")
        .order_by("order", "-created_at")[:8]
    )
    cities = (
        DrivingSchool.objects.filter(is_active=True)
        .exclude(city="")
        .values_list("city", flat=True)
        .distinct()
        .order_by("city")
    )
    return render(
        request,
        "auto_ecole/home.html",
        {
            "schools": schools[:24],
            "featured_courses": featured_courses,
            "cities": cities,
            "query": query,
            "active_city": city,
            "school_count": schools.count(),
        },
    )


def school_detail(request, slug):
    school = get_object_or_404(DrivingSchool, slug=slug, is_active=True)
    courses = school.courses.filter(is_published=True)
    return render(request, "auto_ecole/school_detail.html", {"school": school, "courses": courses})


def course_detail(request, school_slug, course_slug):
    course = get_object_or_404(Course, school__slug=school_slug, slug=course_slug, is_published=True)
    return render(request, "auto_ecole/course_detail.html", {"course": course})


def register_school(request):
    if request.method == "POST":
        form = DrivingSchoolRegistrationForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            with transaction.atomic():
                school = form.save(commit=False)
                if request.user.is_authenticated:
                    owner = request.user
                else:
                    email = form.cleaned_data["email"]
                    if User.objects.filter(email=email).exists():
                        form.add_error("email", "Un compte existe déjà avec cet email. Connectez-vous puis inscrivez votre centre.")
                        return render(request, "auto_ecole/register.html", {"form": form})
                    owner = User.objects.create_user(
                        username=email,
                        email=email,
                        password=form.cleaned_data["password"],
                        first_name=form.cleaned_data["first_name"],
                        last_name=form.cleaned_data["last_name"],
                    )
                    login(request, owner, backend="django.contrib.auth.backends.ModelBackend")
                school.owner = owner
                school.is_active = True
                school.save()
            messages.success(request, "Votre auto-école est enregistrée. Elle est maintenant visible sur E-Shelle Auto-école.")
            return redirect(school.get_absolute_url())
    else:
        form = DrivingSchoolRegistrationForm(user=request.user)
    return render(request, "auto_ecole/register.html", {"form": form})
