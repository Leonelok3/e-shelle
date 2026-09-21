import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from .models import ImmigrationJourney, LearningDraft
from .journey_forms import JourneyForm
from .journey import dashboard_data, sync_preferences, CHECKLIST
from .assessment import QUESTIONS, score_answers


@login_required
@require_http_methods(['GET', 'POST'])
def onboarding(request):
    journey = ImmigrationJourney.objects.filter(user=request.user).first()
    form = JourneyForm(request.POST if request.method == 'POST' else None, instance=journey)
    if request.method == 'POST' and form.is_valid():
        journey = form.save(commit=False)
        journey.user = request.user
        journey.save()
        sync_preferences(request, journey)
        return redirect('immigration97:dashboard' if journey.assessment else 'immigration97:assessment')
    return render(request, 'canada_resume/journey/onboarding.html', {'form': form, 'journey': journey})


@login_required
def dashboard(request):
    journey = ImmigrationJourney.objects.filter(user=request.user).first()
    if not journey:
        return redirect('immigration97:onboarding')
    sync_preferences(request, journey)
    return render(request, 'canada_resume/journey/dashboard.html', dashboard_data(request.user, journey))


@login_required
@require_http_methods(['GET', 'POST'])
def assessment(request):
    journey = ImmigrationJourney.objects.filter(user=request.user).first()
    if not journey:
        return redirect('immigration97:onboarding')
    error, result = '', None
    if request.method == 'POST':
        try:
            result = score_answers(request.POST)
            journey.assessment = {**result, 'completed_at': timezone.now().isoformat()}
            journey.save(update_fields=['assessment', 'updated_at'])
        except ValueError as exc:
            error = str(exc)
    questions = [{'key': key, 'question': question, 'options': options,
                  'selected': request.POST.get(key, '')} for key, question, options, _, _ in QUESTIONS]
    return render(request, 'canada_resume/journey/assessment.html',
                  {'journey': journey, 'questions': questions, 'error': error, 'result': result})


@login_required
@require_POST
def apply_assessment(request):
    journey = ImmigrationJourney.objects.filter(user=request.user).first()
    if journey and journey.assessment.get('suggested_level') in dict(ImmigrationJourney.LEVELS):
        journey.working_level = journey.assessment['suggested_level']
        levels = [item[0] for item in ImmigrationJourney.LEVELS]
        if levels.index(journey.target_level) < levels.index(journey.working_level):
            journey.target_level = journey.working_level
        journey.save(update_fields=['working_level', 'target_level', 'updated_at'])
        sync_preferences(request, journey)
    return redirect('immigration97:dashboard')


@login_required
def dossier(request):
    journey = ImmigrationJourney.objects.filter(user=request.user).first()
    if not journey:
        return redirect('immigration97:onboarding')
    return render(request, 'canada_resume/journey/dossier.html', dashboard_data(request.user, journey))


@login_required
@require_POST
@transaction.atomic
def checklist_update(request):
    journey = ImmigrationJourney.objects.select_for_update().filter(user=request.user).first()
    key = request.POST.get('task')
    if journey and key in {row[0] for row in CHECKLIST}:
        journey.checklist[key] = request.POST.get('done') == '1'
        journey.save(update_fields=['checklist', 'updated_at'])
    return redirect('immigration97:dossier')


@login_required
@require_http_methods(['GET', 'POST'])
def draft(request, exercise_id):
    from preparation_tests.models import CourseExercise
    exercise = CourseExercise.objects.filter(pk=exercise_id, is_active=True,
        lesson__is_published=True, lesson__section='ee').first()
    if not exercise:
        return JsonResponse({'error': 'Exercice indisponible.'}, status=404)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            text = data['text']
            if not isinstance(text, str) or len(text) > 15000:
                raise ValueError
        except (ValueError, TypeError, KeyError):
            return JsonResponse({'error': 'Brouillon invalide.'}, status=400)
        LearningDraft.objects.update_or_create(user=request.user, exercise=exercise, defaults={'text': text})
        return JsonResponse({'saved': True})
    row = LearningDraft.objects.filter(user=request.user, exercise=exercise).first()
    return JsonResponse({'text': row.text if row else '', 'exists': bool(row)})
