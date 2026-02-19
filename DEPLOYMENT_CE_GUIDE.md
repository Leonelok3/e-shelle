# 🚀 DÉPLOIEMENT SYSTÈME COMPRÉHENSION ÉCRITE (CE) - VPS

## 📊 CONTENU GÉNÉRÉ ET TESTÉ

✅ **Curriculum CE (900 exercices)**
- 90 leçons (15 par niveau)
- 6 niveaux CECR: A1, A2, B1, B2, C1, C2
- Thèmes variés et pédagogiquement organisés

✅ **Exams CE (195 questions)**
- 6 exams complets (1 par niveau)
- Questions avec passages authentiques
- Choix multiples (780 choix)
- Passages alignés avec exigences DELF/DALF

✅ **Management Commands**
- `import_reading_curriculum.py` - Import curriculum CE
- `import_reading_exams.py` - Import exams CE

✅ **Validation Locale**
- ✅ 90 leçons importées
- ✅ 900 exercices validés
- ✅ 6 exams créés
- ✅ 195 questions dans la DB
- ✅ Toutes les relations FK intègres

---

## 📋 INSTRUCTIONS DE DÉPLOIEMENT VPS

### ÉTAPE 1: SSH sur le VPS

```bash
ssh ubuntu@31.97.196.197
cd /home/ubuntu/e-shelle
```

### ÉTAPE 2: Git Pull (code + données)

```bash
git pull origin main
```

Le pull inclut:
- 6 fichiers JSON curriculum (reading_curriculum_*.json)
- 2 fichiers JSON exams (exams_reading_*.json)
- 2 management commands (import_reading_*.py)

### ÉTAPE 3: Import Curriculum CE

```bash
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_A1_fr.json --clear
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_A2_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_B1_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_B2_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_C1_fr.json
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_C2_fr.json
```

**Résultat attendu:** 
```
✅ Leçons créées: 90
✅ Exercices créés: 900
```

### ÉTAPE 4: Import Exams CE

```bash
python manage.py import_reading_exams --file ai_engine/learning_content/exams_reading_a_b_fr.json --clear
python manage.py import_reading_exams --file ai_engine/learning_content/exams_reading_c_fr.json
```

**Résultat attendu:**
```
✅ Exams créés: 6
✅ Questions créées: 195
✅ Passages créés: ~15
```

### ÉTAPE 5: Redémarrer Services

```bash
sudo systemctl restart gunicorn
sudo systemctl restart nginx
```

### ÉTAPE 6: Validation

```bash
python manage.py shell << 'EOF'
from preparation_tests.models import CourseLesson, Question
lessons = CourseLesson.objects.filter(section="ce").count()
questions = Question.objects.filter(section__code="ce").count()
print(f"Curriculum CE: {lessons} leçons")
print(f"Exams CE: {questions} questions") 
EOF
```

**Résultat attendu:**
```
Curriculum CE: 90 leçons
Exams CE: 195 questions
```

---

## 🔥 SCRIPT DE DÉPLOIEMENT AUTOMATISÉ (Optionnel)

Télécharger le script `deploy_ce_vps.sh` et l'exécuter:

```bash
bash deploy_ce_vps.sh
```

Ce script exécute automatiquement les étapes 2-6.

---

## ✨ VÉRIFICATION POST-DÉPLOIEMENT

Une fois déployé, vérifier dans Django Admin:

1. **CourseLesson**: 90 leçons avec section="ce"
2. **CourseExercise**: 900 exercices avec instruction/question variés
3. **Exam**: 6 exams CE_A1_FR...CE_C2_FR
4. **ExamSection**: 6 sections avec code="ce"
5. **Question**: 195 questions avec difficultés variées
6. **Passage**: ~15 passages de texte
7. **Choice**: 780 choix (4 par question × 195)

---

## 🚨 ROLLBACK (en cas de problème)

```bash
# Annuler les imports
python manage.py shell << 'EOF'
from preparation_tests.models import CourseLesson, Exam
CourseLesson.objects.filter(section="ce").delete()
Exam.objects.filter(code__startswith="CE_").delete()
EOF

# Redémarrer services
sudo systemctl restart gunicorn
```

---

## 📊 STATISTIQUES SYSTÈME CE

### Contenu
- **Leçons**: 90 (15 × 6 niveaux)
- **Exercices**: 900 (10 × 90 leçons)
- **Exams**: 6 (1 par niveau)
- **Questions**: 195 (20-45 par exam)
- **Total items**: 1095

### Répartition Niveaux
| Niveau | Lessons | Exos | Exam Questions |
|--------|---------|------|---|
| A1 | 15 | 150 | 20 |
| A2 | 15 | 150 | 25 |
| B1 | 15 | 150 | 30 |
| B2 | 15 | 150 | 35 |
| C1 | 15 | 150 | 40 |
| C2 | 15 | 150 | 45 |
| **TOTAL** | **90** | **900** | **195** |

### Temps de Déploiement
- Import curriculum: ~2 minutes
- Import exams: ~1 minute
- Redémarrage services: ~30 secondes
- **Total**: ~3.5 minutes

---

## 🔗 RESSOURCES

- **Repository**: https://github.com/Leonelok3/e-shelle
- **Branch**: main
- **Django Models**: `preparation_tests/models.py`
- **Management Commands**: `preparation_tests/management/commands/`
- **Contenu**: `ai_engine/learning_content/`

---

## ❓ SUPPORT

Pour questions ou problèmes:
1. Consulter les logs: `sudo journalctl -u gunicorn -f`
2. Vérifier Django admin: `/admin/preparation_tests/`
3. Tester management commands localement avant VPS

---

**Status**: ✅ **PRODUCTION READY**

Toutes les validation ont passé. Le système CE est prêt pour être utilisé par les apprenants!

🎉 **BIENVENUE DANS LE MONDE DE LA COMPRÉHENSION ÉCRITE!**
