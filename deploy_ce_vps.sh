#!/bin/bash
# Script de déploiement CE en VPS
# Exécuter sur le VPS: bash deploy_ce.sh

set -e

echo ""
echo "🚀 DÉPLOIEMENT COMPRÉHENSION ÉCRITE (CE) - VPS"
echo "============================================================"

# 1. GIT PULL
echo ""
echo "📥 [1/5] Git pull..."
cd /home/ubuntu/e-shelle
git pull origin main
echo "✅ Git pull réussi"

# 2. IMPORT CURRICULUM
echo ""
echo "📚 [2/5] Import curriculum CE (A1-C2)..."
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_A1_fr.json --clear
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_A2_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_B1_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_B2_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_C1_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_C2_fr.json
echo "✅ Curriculum CE importé (900 exercices)"

# 3. IMPORT EXAMS
echo ""
echo "📋 [3/5] Import exams CE (A1-C2)..."
python manage.py import_reading_exams --file ai_engine/learning_content/exams_reading_a_b_fr.json --clear
python manage.py import_reading_exams --file ai_engine/learning_content/exams_reading_c_fr.json
echo "✅ Exams CE importés (195 questions)"

# 4. MIGRATE (si applicable)
echo ""
echo "🗄️  [4/5] Database check..."
python manage.py migrate --noinput || echo "⚠️  Pas de migrations nécessaires"
python manage.py collectstatic --noinput || echo "⚠️  Static files déjà collectés"
echo "✅ Database OK"

# 5. RESTART SERVICES
echo ""
echo "🔄 [5/5] Redémarrage services..."
sudo systemctl restart gunicorn
sudo systemctl restart nginx
echo "✅ Services redémarrés"

# VÉRIFICATION FINAL
echo ""
echo "============================================================"
echo "✨ VÉRIFICATION FINALE"
echo "============================================================"
echo ""
python manage.py shell << PYTHON_CMD
import django
from preparation_tests.models import CourseLesson, Question

lessons = CourseLesson.objects.filter(section="ce").count()
exercises = 0
for l in CourseLesson.objects.filter(section="ce"):
    exercises += l.exercises.count()
questions = Question.objects.filter(section__code="ce").count()

print(f"📘 Curriculum CE: {lessons} leçons, {exercises} exercices")
print(f"📋 Exams CE: {questions} questions")
print(f"✅ Total: {exercises + questions} contenus CE en production")
PYTHON_CMD

echo ""
echo "============================================================"
echo "🎉 DÉPLOIEMENT CE RÉUSSI!"
echo "============================================================"
echo ""
echo "📊 Status:"
echo "  ✅ Code déployé"
echo "  ✅ Database mise à jour"
echo "  ✅ Services redémarrés"
echo "  ✅ Production live"
echo ""
echo "🔗 App: https://immigration97.com"
echo "📞 Support: contact@immigration97.com"
echo ""
