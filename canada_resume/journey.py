"""A deterministic study schedule driven by the learner's actual activity."""
from datetime import timedelta
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from .models import ImmigrationJourney, ImmigrationAIUsage

SKILLS = {'ce': 'Lire et comprendre', 'co': 'Écouter et comprendre',
          'ee': 'Écrire avec précision', 'eo': 'Prendre la parole'}
CHECKLIST = [
    ('program', 'Explorer le programme adapté à mon projet', 'canada_resume:programs_hub'),
    ('language', 'Vérifier le test de langue demandé', 'preparation_tests:tcf_hub'),
    ('education', 'Rassembler mes diplômes et justificatifs', 'canada_resume:manage_education'),
    ('experience', 'Documenter mes expériences professionnelles', 'canada_resume:manage_experiences'),
    ('cv', 'Préparer mon CV et ma lettre', 'canada_resume:dashboard'),
    ('official', 'Vérifier les exigences sur le site officiel', 'canada_resume:canada_resources'),
]


def sync_preferences(request, journey):
    request.session['french_learning_exam'] = journey.exam
    request.session['french_learning_level'] = journey.working_level


def usage_status(user):
    from django.conf import settings
    limit = max(0, int(getattr(settings, 'IMMIGRATION97_DAILY_AI_LIMIT', 20)))
    row = ImmigrationAIUsage.objects.filter(user=user, day=timezone.localdate()).first()
    used = row.attempts if row else 0
    return {'used': used, 'limit': limit, 'remaining': max(0, limit - used)}


def dashboard_data(user, journey):
    from preparation_tests.models import CourseLesson, UserExerciseProgress, UserLessonProgress
    from preparation_tests.services.learning_coach import learning_dashboard
    learning = learning_dashboard(user, journey.exam, journey.working_level)
    today = timezone.localdate()
    lessons = CourseLesson.objects.filter(is_published=True).filter(
        Q(exam__code__iexact=journey.exam) | Q(exams__code__iexact=journey.exam)).distinct()
    activity = UserExerciseProgress.objects.filter(user=user, lesson__in=lessons)
    completed = UserLessonProgress.objects.filter(user=user, lesson__in=lessons, is_completed=True).values('lesson_id').distinct().count()
    recent_days = set(activity.filter(updated_at__date__gte=today-timedelta(days=6)).values_list('updated_at__date', flat=True))
    reviews = list(activity.filter(is_completed=False, attempts__gt=0).select_related('lesson').order_by('-updated_at')[:4])
    review_cards = [{'title': row.lesson.title, 'skill': SKILLS.get(row.lesson.section, row.lesson.section),
                     'url': reverse('preparation_tests:lesson_session', args=[journey.exam, row.lesson.section, row.lesson_id]) + '#exercise-' + str(row.exercise_id)} for row in reviews]
    if not review_cards:
        for row in activity.filter(is_completed=True, completed_at__date__lte=today-timedelta(days=3)).select_related('lesson').order_by('updated_at')[:2]:
            review_cards.append({'title': row.lesson.title, 'skill': 'Consolider mes acquis',
                'url': reverse('preparation_tests:lesson_session', args=[journey.exam, row.lesson.section, row.lesson_id])})
    schedule = []
    rotation = list(SKILLS)
    start = activity.count() % 4
    for offset in range(7):
        skill = rotation[(start + offset) % 4]
        item = next(row for row in learning['next_lessons'] if row['skill'].lower() == skill)
        schedule.append({'day': today + timedelta(days=offset), 'title': SKILLS[skill],
                         'url': item['url'], 'lesson': item['lesson'], 'minutes': journey.daily_minutes})
    next_action = next((item for item in schedule if item['lesson']), None)
    if review_cards:
        next_action = {'url': review_cards[0]['url'], 'title': 'Reprendre une difficulté', 'minutes': journey.daily_minutes}
    checklist = [{'key': key, 'title': title, 'url': reverse(route), 'done': bool(journey.checklist.get(key))}
                 for key, title, route in CHECKLIST]
    return dict(journey=journey, learning=learning, schedule=schedule, next_action=next_action,
                reviews=review_cards, completed_lessons=completed, active_days=len(recent_days),
                exercise_count=activity.filter(attempts__gt=0).count(), checklist=checklist,
                checklist_done=sum(row['done'] for row in checklist), usage=usage_status(user))
