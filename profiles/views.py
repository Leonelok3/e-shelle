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
from .models import RecruiterFavorite
from .models import RecruiterFavorite

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
            InterviewInvite.objects.create(
                recruiter=request.user,
                candidate_user=self.object.user,
                subject="Invitation à entretien",
                message=form.cleaned_data["message"],
            )
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

    invite.status = "accepted"
    invite.save(update_fields=["status"])
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

    invite.status = "declined"
    invite.save(update_fields=["status"])
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
