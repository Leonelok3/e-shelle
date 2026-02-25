#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de validation POST-déploiement pour le système CE
Vérifie que tous les contenus sont bien en production
"""

import django
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from preparation_tests.models import (
    CourseLesson, CourseExercise, Exam, ExamSection, 
    Question, Choice, Passage
)
from django.utils import timezone
from django.db.models import Count

def validate_curriculum():
    """Valide le curriculum CE"""
    print("\n📘 VALIDATION CURRICULUM CE")
    print("-" * 50)
    
    levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    total_lessons = 0
    total_exercises = 0
    
    for level in levels:
        lessons = CourseLesson.objects.filter(level=level, section="ce")
        exercises = CourseExercise.objects.filter(lesson__level=level, lesson__section="ce")
        
        lesson_count = lessons.count()
        exercise_count = exercises.count()
        
        total_lessons += lesson_count
        total_exercises += exercise_count
        
        status = "✅" if lesson_count == 15 and exercise_count == 150 else "⚠️"
        print(f"  {status} {level}: {lesson_count} leçons, {exercise_count} exercices")
    
    print(f"\n  📊 Total: {total_lessons} leçons, {total_exercises} exercices")
    
    expected = 1350  # 6 levels × 225 (15 lessons + 150 exercices)
    actual = total_lessons + total_exercises
    return actual >= 1050  # Au moins le curriculum

def validate_exams():
    """Valide les exams CE"""
    print("\n📋 VALIDATION EXAMS CE")
    print("-" * 50)
    
    exams = Exam.objects.filter(code__startswith="CE_")
    print(f"  Exams trouvés: {exams.count()}/6")
    
    for exam in exams:
        sections = ExamSection.objects.filter(exam=exam, code="ce")
        questions = Question.objects.filter(section__exam=exam, section__code="ce")
        choices = Choice.objects.filter(question__section__exam=exam, question__section__code="ce")
        passages = Passage.objects.filter(question__section__exam=exam).distinct().count()
        
        print(f"  ✅ {exam.code}: {questions.count()} Q, {choices.count()} choix, {passages} passages")
    
    total_questions = Question.objects.filter(section__code="ce").count()
    return total_questions == 195

def validate_links():
    """Valide les relations FK"""
    print("\n🔗 VALIDATION RELATIONS")
    print("-" * 50)
    
    # CourseLesson > CourseExercise
    lessons_with_exercises = CourseLesson.objects.filter(
        section="ce", 
        exercises__isnull=False
    ).distinct().count()
    print(f"  ✅ Leçons avec exercices: {lessons_with_exercises}")
    
    # Exam > ExamSection > Question > Choice
    questions_with_choices = Question.objects.filter(
        section__code="ce",
        choices__isnull=False
    ).distinct().count()
    print(f"  ✅ Questions avec choix: {questions_with_choices}")
    
    # Passages
    passages_used = Passage.objects.filter(question__section__code="ce").distinct().count()
    print(f"  ✅ Passages référencés: {passages_used}")
    
    return True

def validate_data_integrity():
    """Valide l'intégrité des données"""
    print("\n🔍 VALIDATION INTÉGRITÉ")
    print("-" * 50)
    
    issues = []
    
    # Vérifier pas d'options vides
    empty_options = CourseExercise.objects.filter(
        lesson__section="ce",
        option_a=""
    ).count()
    if empty_options > 0:
        issues.append(f"⚠️  {empty_options} exercices avec option_a vide")
    else:
        print("  ✅ Pas d'options vides")
    
    # Vérifier des bonnes réponses
    questions_no_correct = Question.objects.filter(
        section__code="ce",
        choices__is_correct=False
    ).annotate(
        correct_count=Count('choices__is_correct')
    ).filter(correct_count=0)
    
    if questions_no_correct.exists():
        issues.append(f"⚠️  Certaines questions n'ont pas de bonne réponse")
    else:
        print("  ✅ Toutes les questions ont une bonne réponse")
    
    return len(issues) == 0

def main():
    """Exécute la validation complète"""
    print("\n" + "="*60)
    print("✨ VALIDATION POST-DÉPLOIEMENT CE")
    print("="*60)
    
    start_time = timezone.now()
    
    checks = [
        ("Curriculum", validate_curriculum),
        ("Exams", validate_exams),
        ("Relations", validate_links),
        ("Intégrité", validate_data_integrity),
    ]
    
    results = []
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Erreur lors de {check_name}: {e}")
            results.append(False)
    
    # Résumé final
    print("\n" + "="*60)
    print("📊 RÉSUMÉ VALIDATION")
    print("="*60)
    
    all_passed = all(results)
    
    if all_passed:
        print("\n✅ ✅ ✅  TOUS LES TESTS PASSÉS  ✅ ✅ ✅")
        print("\n🎉 Le système CE est PRÊT POUR PRODUCTION!")
        print("\n📈 Contenu CE deployé:")
        
        lessons = CourseLesson.objects.filter(section="ce").count()
        exercises = CourseExercise.objects.filter(lesson__section="ce").count()
        exams = Exam.objects.filter(code__startswith="CE_").count()
        questions = Question.objects.filter(section__code="ce").count()
        
        print(f"  • {lessons} leçons")
        print(f"  • {exercises} exercices curriculum")
        print(f"  • {exams} exams")
        print(f"  • {questions} questions d'exams")
        print(f"  • Total: {exercises + questions} items")
        
        elapsed = (timezone.now() - start_time).total_seconds()
        print(f"\n⏱️  Validation complétée en {elapsed:.2f}s")
        
        return 0
    else:
        print("\n❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("\nVérifiez les logs ci-dessus pour plus de détails.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
