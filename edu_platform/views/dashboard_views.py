"""
Vues de l'espace étudiant EduCam Pro.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.utils import timezone

from edu_platform.models import Subject, AccessCode, VideoLesson


class EduLoginRequiredMixin(LoginRequiredMixin):
    """Mixin qui redirige vers la page de login EduCam."""
    login_url = '/edu/login/'


class StudentDashboardView(EduLoginRequiredMixin, View):
    """Tableau de bord principal de l'étudiant."""
    template_name = 'edu_platform/dashboard/home.html'

    def get(self, request):
        user = request.user
        active_code = AccessCode.objects.filter(
            activated_by=user,
            status='active',
        ).select_related('plan').first()

        if not active_code:
            return redirect('edu:activate_code')

        # Matières récentes
        subjects = Subject.objects.filter(is_published=True).order_by('-updated_at')[:6]
        # Vidéos récentes
        recent_videos = VideoLesson.objects.filter(
            subject__is_published=True
        ).select_related('subject').order_by('-created_at')[:4]

        # Jours restants
        days_left = None
        if active_code.expires_at:
            delta = active_code.expires_at - timezone.now()
            days_left = max(0, delta.days)

        context = {
            'active_code': active_code,
            'days_left': days_left,
            'subjects': subjects,
            'recent_videos': recent_videos,
            'subjects_by_level': self._get_subjects_by_level(),
        }
        return render(request, self.template_name, context)

    def _get_subjects_by_level(self):
        from django.db.models import Count
        return Subject.objects.filter(is_published=True).values(
            'level'
        ).annotate(count=Count('id')).order_by('level')


class ProfileView(EduLoginRequiredMixin, View):
    """Profil de l'étudiant."""
    template_name = 'edu_platform/dashboard/profile.html'

    def get(self, request):
        try:
            edu_profile = request.user.edu_profile
        except Exception:
            edu_profile = None

        devices = []
        if request.user.edu_devices.exists():
            devices = request.user.edu_devices.all().select_related('access_code')[:5]

        context = {
            'edu_profile': edu_profile,
            'devices': devices,
        }
        return render(request, self.template_name, context)
