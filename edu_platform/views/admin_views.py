"""
Vues back-office admin custom EduCam Pro.
Accessible uniquement aux superusers ou staff avec permission edu_admin.
"""
import csv
import logging
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta

from edu_platform.models import (
    EduProfile, AccessCode, PaymentTransaction,
    Subject, ExamDocument, VideoLesson, DeviceBinding
)

logger = logging.getLogger('edu_platform')


class StaffRequiredMixin:
    """Mixin qui exige le statut staff."""
    @method_decorator(staff_member_required(login_url='/edu/login/'))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class EduAdminDashboardView(StaffRequiredMixin, View):
    """Tableau de bord admin avec statistiques."""
    template_name = 'edu_platform/admin_custom/dashboard.html'

    def get(self, request):
        now = timezone.now()
        last_30 = now - timedelta(days=30)

        stats = {
            'total_users': EduProfile.objects.count(),
            'active_subscriptions': AccessCode.objects.filter(status='active', expires_at__gt=now).count(),
            'total_revenue': PaymentTransaction.objects.filter(
                status='confirmed'
            ).aggregate(total=Sum('amount_xaf'))['total'] or 0,
            'revenue_30d': PaymentTransaction.objects.filter(
                status='confirmed', confirmed_at__gte=last_30
            ).aggregate(total=Sum('amount_xaf'))['total'] or 0,
            'pending_transactions': PaymentTransaction.objects.filter(status__in=['pending', 'initiated']).count(),
            'total_subjects': Subject.objects.filter(is_published=True).count(),
            'total_videos': VideoLesson.objects.count(),
            'total_documents': ExamDocument.objects.count(),
            'new_users_30d': EduProfile.objects.filter(created_at__gte=last_30).count(),
        }

        recent_transactions = PaymentTransaction.objects.filter(
            status='confirmed'
        ).select_related('user', 'plan').order_by('-confirmed_at')[:10]

        context = {
            'stats': stats,
            'recent_transactions': recent_transactions,
        }
        return render(request, self.template_name, context)


class EduUserListView(StaffRequiredMixin, View):
    """Liste des utilisateurs avec statut abonnement."""
    template_name = 'edu_platform/admin_custom/users.html'

    def get(self, request):
        search = request.GET.get('q', '')
        profiles = EduProfile.objects.select_related('user').order_by('-created_at')
        if search:
            profiles = profiles.filter(
                Q(user__email__icontains=search) |
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(phone_number__icontains=search)
            )
        return render(request, self.template_name, {'profiles': profiles, 'search': search})


class AccessCodeListView(StaffRequiredMixin, View):
    """Liste et gestion des codes d'accès."""
    template_name = 'edu_platform/admin_custom/codes.html'

    def get(self, request):
        status_filter = request.GET.get('status', '')
        codes = AccessCode.objects.select_related('plan', 'activated_by', 'transaction')
        if status_filter:
            codes = codes.filter(status=status_filter)
        codes = codes.order_by('-generated_at')[:200]

        return render(request, self.template_name, {
            'codes': codes,
            'status_filter': status_filter,
            'status_choices': AccessCode.STATUS_CHOICES,
        })

    def post(self, request):
        """Révoquer un code."""
        code_pk = request.POST.get('revoke_code_pk')
        if code_pk:
            try:
                code = AccessCode.objects.get(pk=code_pk)
                code.status = 'revoked'
                code.save(update_fields=['status'])
                logger.info('Code %s révoqué par admin %s', code.code, request.user.username)
            except AccessCode.DoesNotExist:
                pass
        return redirect('edu:admin_codes')


class ContentManagerView(StaffRequiredMixin, View):
    """Gestionnaire de contenu : matières, documents, vidéos."""
    template_name = 'edu_platform/admin_custom/content_manager.html'

    def get(self, request):
        from edu_platform.forms.content_forms import SubjectForm, ExamDocumentForm, VideoLessonForm
        subjects = Subject.objects.annotate(
            doc_count=Count('documents'),
            video_count=Count('videos')
        ).order_by('level', 'order')

        subject_form = SubjectForm()
        doc_form = ExamDocumentForm()
        video_form = VideoLessonForm()

        return render(request, self.template_name, {
            'subjects': subjects,
            'subject_form': subject_form,
            'doc_form': doc_form,
            'video_form': video_form,
        })

    def post(self, request):
        from edu_platform.forms.content_forms import SubjectForm, ExamDocumentForm, VideoLessonForm
        action = request.POST.get('action', '')

        if action == 'add_subject':
            form = SubjectForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                from django.contrib import messages
                messages.success(request, "Matière ajoutée avec succès.")
            else:
                from django.contrib import messages
                messages.error(request, f"Erreur : {form.errors}")

        elif action == 'add_document':
            form = ExamDocumentForm(request.POST, request.FILES)
            if form.is_valid():
                doc = form.save()
                if doc.file:
                    doc.file_size_kb = doc.file.size // 1024
                    doc.save(update_fields=['file_size_kb'])
                from django.contrib import messages
                messages.success(request, "Document ajouté avec succès.")

        elif action == 'add_video':
            form = VideoLessonForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                from django.contrib import messages
                messages.success(request, "Vidéo ajoutée avec succès.")

        return redirect('edu:admin_content')


class TransactionListView(StaffRequiredMixin, View):
    """Historique des transactions."""
    template_name = 'edu_platform/admin_custom/transactions.html'

    def get(self, request):
        status_filter = request.GET.get('status', '')
        provider_filter = request.GET.get('provider', '')

        transactions = PaymentTransaction.objects.select_related('user', 'plan').order_by('-created_at')
        if status_filter:
            transactions = transactions.filter(status=status_filter)
        if provider_filter:
            transactions = transactions.filter(provider=provider_filter)

        transactions = transactions[:300]

        return render(request, self.template_name, {
            'transactions': transactions,
            'status_filter': status_filter,
            'provider_filter': provider_filter,
            'status_choices': PaymentTransaction.STATUS_CHOICES,
            'provider_choices': PaymentTransaction.PROVIDER_CHOICES,
        })


class DeviceListView(StaffRequiredMixin, View):
    """Liste des appareils enregistrés."""
    template_name = 'edu_platform/admin_custom/devices.html'

    def get(self, request):
        devices = DeviceBinding.objects.select_related(
            'user', 'access_code', 'access_code__plan'
        ).order_by('-last_seen')[:200]

        return render(request, self.template_name, {'devices': devices})


class ExportSubscribersView(StaffRequiredMixin, View):
    """Export CSV des abonnés actifs."""
    def get(self, request):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="abonnes_actifs.csv"'

        writer = csv.writer(response)
        writer.writerow(['Nom', 'Email', 'Téléphone', 'Plan', 'Expiration', 'Appareil'])

        codes = AccessCode.objects.filter(
            status='active',
            expires_at__gt=timezone.now()
        ).select_related('activated_by', 'plan')

        for code in codes:
            user = code.activated_by
            if not user:
                continue
            try:
                phone = user.edu_profile.phone_number
            except Exception:
                phone = ''
            binding = code.device_bindings.filter(is_primary=True).first()
            device_label = binding.device_label if binding else ''

            writer.writerow([
                user.get_full_name() or user.username,
                user.email,
                phone,
                code.plan.name,
                code.expires_at.strftime('%d/%m/%Y') if code.expires_at else '',
                device_label,
            ])

        return response
