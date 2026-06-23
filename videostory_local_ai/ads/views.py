from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from threading import Thread

from .forms import BusinessForm, PhotoUploadForm, AdCreateForm
from businesses.models import BusinessPhoto, Business
from .models import AdProject
from agents.ad_orchestrator import AdOrchestrator


def dashboard(request):
    projects = AdProject.objects.all().order_by('-created_at')
    return render(request, 'ads/dashboard.html', {'projects': projects})


def create_ad(request):
    if request.method == 'POST':
        bform = BusinessForm(request.POST)
        pform = PhotoUploadForm(request.POST, request.FILES)
        aform = AdCreateForm(request.POST)
        if bform.is_valid() and aform.is_valid():
            business = bform.save()
            files = request.FILES.getlist('photos')
            if len(files) < 3 or len(files) > 10:
                # re-render with an error
                return render(request, 'ads/create_ad.html', {
                    'bform': bform,
                    'pform': pform,
                    'aform': aform,
                    'error': 'Veuillez télécharger entre 3 et 10 photos.',
                })
            for i, f in enumerate(files[:10], start=1):
                BusinessPhoto.objects.create(business=business, image=f, order=i)
            ad = aform.save(commit=False)
            ad.business = business
            ad.save()
            return redirect(reverse('ads:project_detail', args=[ad.pk]))
    else:
        bform = BusinessForm()
        pform = PhotoUploadForm()
        aform = AdCreateForm()
    return render(request, 'ads/create_ad.html', {'bform': bform, 'pform': pform, 'aform': aform})


def project_list(request):
    projects = AdProject.objects.all().order_by('-created_at')
    return render(request, 'ads/projects.html', {'projects': projects})


def project_detail(request, pk):
    project = get_object_or_404(AdProject, pk=pk)
    return render(request, 'ads/project_detail.html', {'project': project})


@require_POST
def start_render(request, pk):
    project = get_object_or_404(AdProject, pk=pk)

    def run_orchestrator(ad_id):
        ad = AdProject.objects.get(pk=ad_id)
        orchestrator = AdOrchestrator(ad)
        orchestrator.run()

    thread = Thread(target=run_orchestrator, args=(project.pk,))
    thread.daemon = True
    thread.start()
    return JsonResponse({'status': 'started'})
