from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse

from billing.services import has_active_access, has_session_access
from cv_generator.models import CV

from .models import Profile, Category
from .forms import ProfileForm, PortfolioItemForm, ContactCandidateForm, AvatarUploadForm

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import RecruiterFavorite, ProfileView

# ======================================================
# LISTE DES PROFILS (visible aux recruteurs)
# ======================================================
class ProfileListView(ListView):
    model = Profile
    template_name = "profiles/profile_list.html"
    context_object_name = "profiles"
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()

        # ✅ uniquement profils publiés
        queryset = queryset.filter(is_public=True)

        category = self.request.GET.get("category")
        query = self.request.GET.get("q")

        if category:
            queryset = queryset.filter(category__slug=category)

        if query:
            queryset = queryset.filter(
                Q(headline__icontains=query) |
                Q(bio__icontains=query) |
                Q(location__icontains=query)
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Category.objects.all()
        return context


# ======================================================
# DETAIL D'UN PROFIL (page recruteur)
# + envoi d'invitation
# ======================================================
# profiles/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import DetailView
from django.contrib import messages

from billing.services import has_active_access
from recruiters.models import InterviewInvite
from .models import Profile
from .forms import ContactCandidateForm
from django.db import models


class ProfileDetailView(DetailView):
    model = Profile
    template_name = "profiles/profile_detail.html"
    context_object_name = "profile"
    

    def get_queryset(self):
        """
        - Recruteur/public: seulement les profils publiés
        - Propriétaire: peut voir même si non publié
        """
        qs = super().get_queryset()
        if self.request.user.is_authenticated:
            return qs.filter(models.Q(is_public=True) | models.Q(user=self.request.user))
        return qs.filter(is_public=True)

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        # Track profile view (only from others, not from owner)
        if request.user.is_authenticated and request.user != self.object.user:
            ProfileView.objects.create(profile=self.object, viewer=request.user)
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["contact_form"] = ContactCandidateForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ContactCandidateForm(request.POST)

        # ✅ Doit être connecté
        if not request.user.is_authenticated:
            messages.error(request, "Connectez-vous pour envoyer une invitation.")
            return redirect("authentification:login")

        # ✅ Option: Premium requis côté recruteur (recommandé)
        if not has_active_access(request.user):
            messages.error(request, "Accès Premium requis pour envoyer une invitation.")
            return redirect("billing:access")

        if form.is_valid():
            invite = InterviewInvite.objects.create(
                recruiter=request.user,
                candidate_user=self.object.user,
                subject="Invitation à entretien",
                message=form.cleaned_data["message"],
            )
            from recruiters.emails import send_invite_received
            send_invite_received(invite)
            messages.success(request, "✅ Invitation envoyée. Le candidat pourra répondre depuis son espace.")
            return redirect("profiles:detail", pk=self.object.pk)

        context = self.get_context_data()
        context["contact_form"] = form
        return render(request, self.template_name, context)


# ======================================================
# CREATION DE PROFIL
# ======================================================
class ProfileCreateView(LoginRequiredMixin, CreateView):
    model = Profile
    form_class = ProfileForm
    template_name = "profiles/profile_form.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Profil créé avec succès !")
        return super().form_valid(form)


# ======================================================
# EDITION DE PROFIL
# ======================================================
class ProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "profiles/profile_form.html"

    def test_func(self):
        return self.request.user == self.get_object().user

    def get_success_url(self):
        return reverse("profiles:my_space")


# ======================================================
# AJOUT PORTFOLIO
# ======================================================
@login_required
def add_portfolio_item(request, pk):
    profile = get_object_or_404(Profile, pk=pk)

    if request.user != profile.user:
        return redirect("profiles:list")

    if request.method == "POST":
        form = PortfolioItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.profile = profile
            item.save()
            messages.success(request, "✅ Document ajouté au portfolio.")
            return redirect("profiles:detail", pk=pk)
    else:
        form = PortfolioItemForm()

    return render(
        request,
        "profiles/portfolio_form.html",
        {"form": form, "profile": profile},
    )


# ======================================================
# MON ESPACE CANDIDAT
# ======================================================
@login_required
def my_space(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    has_premium = has_active_access(request.user)
    has_temp_access = has_session_access(request)

    # ✅ Si pas premium, on force le profil en non-public
    if not has_premium and profile.is_public:
        profile.is_public = False
        profile.save(update_fields=["is_public"])

    # ✅ IMPORTANT : ton modèle CV utilise "user" (pas "utilisateur")
    recent_cvs = CV.objects.filter(user=request.user).order_by("-created_at")[:5]

    test_results = []

    context = {
        "profile": profile,
        "has_premium": has_premium,
        "has_temp_access": has_temp_access,
        "recent_cvs": recent_cvs,
        "test_results": test_results,
    }
    return render(request, "profiles/my_space.html", context)


# ======================================================
# UPLOAD AVATAR
# ======================================================
@login_required
def upload_avatar(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        form = AvatarUploadForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Photo de profil mise à jour.")
            return redirect("profiles:my_space")
    else:
        form = AvatarUploadForm(instance=profile)

    return render(
        request,
        "profiles/avatar_upload.html",
        {"profile": profile, "form": form},
    )


# ======================================================
# TOGGLE VISIBILITE (PUBLIC/PRIVATE)
# ======================================================
@require_POST
@login_required
def toggle_public(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)

    has_premium = has_active_access(request.user)
    if not has_premium:
        messages.error(request, "🔒 Accès Premium requis pour publier votre profil.")
        return redirect("profiles:my_space")

    profile.is_public = not profile.is_public
    profile.save(update_fields=["is_public"])

    if profile.is_public:
        messages.success(request, "✅ Profil publié : visible par les recruteurs.")
    else:
        messages.success(request, "Profil dépublié : vous n’êtes plus visible.")
    return redirect("profiles:my_space")


# ======================================================
# INVITATIONS — CANDIDAT (reçues)
# ======================================================
@login_required
def my_invitations(request):
    from recruiters.models import InterviewInvite

    profile, _ = Profile.objects.get_or_create(user=request.user)

    invites = InterviewInvite.objects.filter(
        candidate_user=request.user
    ).order_by("-created_at")

    return render(
        request,
        "profiles/my_invitations.html",
        {"invites": invites, "profile": profile},
    )


# ======================================================
# INVITATIONS — ACTIONS CANDIDAT
# ======================================================
@require_POST
@login_required
def invite_accept(request, invite_id):
    from recruiters.models import InterviewInvite

    invite = get_object_or_404(
        InterviewInvite,
        id=invite_id,
        candidate_user=request.user
    )

    if invite.status != "sent":
        messages.info(request, "Cette invitation a déjà été traitée.")
        return redirect("profiles:my_invitations")

    invite.accept()
    from recruiters.emails import send_invite_accepted
    send_invite_accepted(invite)
    messages.success(request, "✅ Invitation acceptée.")
    return redirect("profiles:my_invitations")


@require_POST
@login_required
def invite_decline(request, invite_id):
    from recruiters.models import InterviewInvite

    invite = get_object_or_404(
        InterviewInvite,
        id=invite_id,
        candidate_user=request.user
    )

    if invite.status != "sent":
        messages.info(request, "Cette invitation a déjà été traitée.")
        return redirect("profiles:my_invitations")

    invite.decline()
    from recruiters.emails import send_invite_declined
    send_invite_declined(invite)
    messages.success(request, "Invitation refusée.")
    return redirect("profiles:my_invitations")


# ======================================================
# INVITATIONS — RECRUTEUR (envoyées)
# ======================================================
@login_required
def recruiter_invites(request):
    from recruiters.models import InterviewInvite

    invites = InterviewInvite.objects.filter(
        recruiter=request.user
    ).order_by("-created_at")

    return render(
        request,
        "profiles/recruiter_invites.html",
        {"invites": invites},
    )
@login_required
def favorites_list(request):
    favorites = RecruiterFavorite.objects.filter(
        recruiter=request.user
    ).select_related("profile", "profile__user", "profile__category").order_by("-created_at")

    return render(request, "profiles/favorites_list.html", {"favorites": favorites})


@require_POST
@login_required
def toggle_favorite(request, pk):
    profile = get_object_or_404(Profile, pk=pk)

    obj, created = RecruiterFavorite.objects.get_or_create(
        recruiter=request.user,
        profile=profile
    )

    if not created:
        obj.delete()
        messages.success(request, "Retiré des favoris.")
    else:
        messages.success(request, "Ajouté aux favoris ⭐")

    # Retour à la page précédente (list ou detail)
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", reverse("profiles:list")))



def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    context["categories"] = Category.objects.all()

    fav_ids = set()
    if self.request.user.is_authenticated:
        fav_ids = set(
            RecruiterFavorite.objects.filter(recruiter=self.request.user)
            .values_list("profile_id", flat=True)
        )
    context["fav_ids"] = fav_ids
    return context


# ======================================================
# ANALYTICS CANDIDAT
# ======================================================
@login_required
def my_analytics(request):
    from recruiters.models import InterviewInvite
    from django.db.models import Count
    from django.db.models.functions import TruncMonth

    try:
        profile = Profile.objects.get(user=request.user)
    except Profile.DoesNotExist:
        profile = None

    total_views = 0
    invites_received = 0
    invites_accepted = 0
    invites_declined = 0
    monthly_views_labels = []
    monthly_views_data = []

    if profile:
        total_views = profile.views.count()
        monthly = list(
            profile.views
            .annotate(month=TruncMonth("viewed_at"))
            .values("month")
            .annotate(count=Count("id"))
            .order_by("month")[:6]
        )
        monthly_views_labels = [m["month"].strftime("%b %Y") if m["month"] else "" for m in monthly]
        monthly_views_data = [m["count"] for m in monthly]

    invites_qs = InterviewInvite.objects.filter(candidate_user=request.user)
    invites_received = invites_qs.count()
    invites_accepted = invites_qs.filter(status="accepted").count()
    invites_declined = invites_qs.filter(status="declined").count()
    invites_pending = invites_qs.filter(status="sent").count()

    # Completion score (simple)
    if profile:
        fields = [profile.headline, profile.bio, profile.location, profile.avatar, profile.linkedin_url]
        completion = int(sum(1 for f in fields if f) / len(fields) * 100)
    else:
        completion = 0

    return render(request, "profiles/my_analytics.html", {
        "profile": profile,
        "total_views": total_views,
        "monthly_views_labels": monthly_views_labels,
        "monthly_views_data": monthly_views_data,
        "invites_received": invites_received,
        "invites_accepted": invites_accepted,
        "invites_declined": invites_declined,
        "invites_pending": invites_pending,
        "completion": completion,
    })
