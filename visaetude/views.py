from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import (
    Country, UserProfile, CountryGuide,
    RequiredDocument, UserChecklist, FAQ, Milestone
)
from .forms import UserProfileForm, ChecklistUpdateForm


# --- Pages publiques ---

def home(request):
    countries = Country.objects.filter(actif=True).order_by('nom')
    faqs = FAQ.objects.filter(populaire=True)[:5]
    context = {
        'countries': countries,
        'faqs': faqs,
    }
    return render(request, 'visaetude/home.html', context)


# --- Espace connecté (protégé par le login GLOBAL défini dans settings.LOGIN_URL) ---

@login_required()
def profile(request):
    profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil mis à jour avec succès !')
            return redirect('visaetude:profile')
    else:
        form = UserProfileForm(instance=profile)

    total_documents = UserChecklist.objects.filter(user=request.user).count()
    documents_completes = UserChecklist.objects.filter(
        user=request.user, statut='complete'
    ).count()
    progression = (documents_completes / total_documents * 100) if total_documents else 0

    context = {
        'form': form,
        'profile': profile,
        'progression': round(progression, 2),
        'total_documents': total_documents,
        'documents_completes': documents_completes,
    }
    return render(request, 'visaetude/profile.html', context)


@login_required()
def country_guide(request, country_code):
    country = get_object_or_404(Country, code=country_code)
    guides = CountryGuide.objects.filter(pays=country).order_by('id')
    documents = RequiredDocument.objects.filter(pays=country).order_by('id')
    faqs = FAQ.objects.filter(pays=country).order_by('id')

    context = {
        'country': country,
        'guides': guides,
        'documents': documents,
        'faqs': faqs,
    }
    return render(request, 'visaetude/country_guide.html', context)


@login_required()
def checklist(request, country_code):
    country = get_object_or_404(Country, code=country_code)
    documents = RequiredDocument.objects.filter(pays=country)

    # Initialiser la checklist si besoin
    for doc in documents:
        UserChecklist.objects.get_or_create(
            user=request.user, pays=country, document=doc
        )

    items = (
        UserChecklist.objects
        .filter(user=request.user, pays=country)
        .select_related('document', 'pays')
        .order_by('document__id')
    )

    total = items.count()
    completed = items.filter(statut='complete').count()
    progression = (completed / total * 100) if total else 0

    context = {
        'country': country,
        'checklist_items': items,
        'progression': round(progression, 2),
        'total': total,
        'completed': completed,
    }
    return render(request, 'visaetude/checklist.html', context)


@login_required()
def update_checklist_item(request, item_id):
    item = get_object_or_404(UserChecklist, id=item_id, user=request.user)

    if request.method == 'POST':
        form = ChecklistUpdateForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Document mis à jour !')
            return redirect('visaetude:checklist', country_code=item.pays.code)
    else:
        form = ChecklistUpdateForm(instance=item)

    context = {'form': form, 'item': item}
    return render(request, 'visaetude/update_checklist.html', context)


def countries_list(request):
    countries = Country.objects.filter(actif=True).order_by('nom')
    return render(request, 'visaetude/countries_list.html', {'countries': countries})
