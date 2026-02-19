#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick validation script - Vérification rapide CE
"""

import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from preparation_tests.models import CourseLesson, CourseExercise, Exam, Question, Choice

print("\n" + "="*60)
print("✨ VÉRIFICATION RAPIDE CE - ALL SYSTEMS GO!")
print("="*60 + "\n")

# Curriculum
l = CourseLesson.objects.filter(section="ce").count()
e = CourseExercise.objects.filter(lesson__section="ce").count()
print(f"📘 Curriculum CE: {l} leçons, {e} exercices")

# Exams
x = Exam.objects.filter(code__startswith="CE_").count()
q = Question.objects.filter(section__code="ce").count()
c = Choice.objects.filter(question__section__code="ce").count()
print(f"📋 Exams CE: {x} exams, {q} questions, {c} choix")

# Total
total = e + q
print(f"\n🎯 TOTAL: {total} items CE en base de données\n")

if l == 90 and e == 900 and x == 6 and q == 195:
    print("="*60)
    print("✅ ✅ ✅  VALIDATION RÉUSSIE - READY FOR PRODUCTION!")
    print("="*60 + "\n")
else:
    print("⚠️ Certains chiffres ne correspondent pas")
    print(f"  Expected: 90 leçons, 900 exos, 6 exams, 195 questions")
    print(f"  Got: {l} leçons, {e} exos, {x} exams, {q} questions\n")
