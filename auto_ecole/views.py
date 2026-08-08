from django.shortcuts import render, get_object_or_404

from .models import DrivingSchool, Course


def home(request):
    schools = DrivingSchool.objects.filter(is_active=True)[:12]
    featured_courses = Course.objects.filter(is_published=True).select_related("school")[:8]
    return render(request, "auto_ecole/home.html", {"schools": schools, "featured_courses": featured_courses})


def school_detail(request, slug):
    school = get_object_or_404(DrivingSchool, slug=slug, is_active=True)
    courses = school.courses.filter(is_published=True)
    return render(request, "auto_ecole/school_detail.html", {"school": school, "courses": courses})


def course_detail(request, school_slug, course_slug):
    course = get_object_or_404(Course, school__slug=school_slug, slug=course_slug, is_published=True)
    return render(request, "auto_ecole/course_detail.html", {"course": course})
