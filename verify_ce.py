#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Quick verification script"""
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from preparation_tests.models import CourseLesson, CourseExercise, Question, ExamSection, Exam

print("\n" + "="*60)
print("📊 VÉRIFICATION BASE DE DONNÉES CE")
print("="*60)

# Curriculum
lessons = CourseLesson.objects.filter(section="ce")
print(f"\n📘 CURRICULUM CE")
print(f"  ✅ Leçons: {lessons.count()}")
print(f"  ✅ Exercices: {CourseExercise.objects.filter(lesson__section='ce').count()}")
print(f"  Niveaux: {lessons.values_list('level', flat=True).distinct()}")

# Exams
exams = Exam.objects.filter(code__startswith="CE_")
print(f"\n📋 EXAMS CE")
print(f"  ✅ Exams: {exams.count()}")
print(f"  ✅ Sections: {ExamSection.objects.filter(code='ce').count()}")
print(f"  ✅ Questions: {Question.objects.filter(section__code='ce').count()}")
for exam in exams:
    print(f"    - {exam.code}")

print("\n" + "="*60)
print("✨ RÉSUMÉ PRODUCTION CE READY")
print("="*60)
total_ex_curriculum = CourseExercise.objects.filter(lesson__section='ce').count()
total_q_exams = Question.objects.filter(section__code='ce').count()
print(f"Total exercices curriculum: {total_ex_curriculum}")
print(f"Total questions exams: {total_q_exams}")
print(f"Total contenu CE: {total_ex_curriculum + total_q_exams}")
print("="*60 + "\n")
