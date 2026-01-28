from __future__ import annotations

from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import Lesson, LessonProgress

def mark_completed(user, lesson: Lesson) -> LessonProgress:
    prog, _ = LessonProgress.objects.get_or_create(user=user, lesson=lesson)
    prog.is_completed = True
    prog.completed_at = prog.completed_at or timezone.now()
    prog.save(update_fields=["is_completed", "completed_at", "updated_at"])
    return prog
