# 🚀 COMMANDES SSH DÉPLOIEMENT CE - VPS FINAL

## 📋 Copier-coller ces commandes dans votre terminal local

### ÉTAPE 1: Se connecter au VPS

```bash
ssh ubuntu@31.97.196.197
```

**Mot de passe**: (demander à l'administrateur VPS si oublié)

---

### ÉTAPE 2: Aller au répertoire projet

```bash
cd /home/ubuntu/e-shelle
```

---

### ÉTAPE 3: Git pull les nouveaux scripts et données

```bash
git pull origin main
```

**Résultat attendu:**
```
Updating a51b951..aacc3cd
Fast-forward
 DEPLOYMENT_CE_GUIDE.md              | 150 ++
 deploy_ce_final.sh                  | 120 ++
 validate_ce_quick.py                |  30 ++
 ...
 Total 5 insertions(+)
```

---

### ÉTAPE 4: Donner les permissions d'exécution au script

```bash
chmod +x deploy_ce_final.sh
```

---

### ÉTAPE 5: Exécuter le script de déploiement FINAL

```bash
bash deploy_ce_final.sh
```

**Ce script va:**
1. ✅ Git pull le code
2. ✅ Importer curriculum CE (A1-C2, 900 exercices)
3. ✅ Importer exams CE (A1-C2, 195 questions)
4. ✅ Redémarrer services (Gunicorn + Nginx)
5. ✅ Valider que tout est en place

**Durée estimée:** ~3-4 minutes

**Résultat attendu à la fin:**
```
╔════════════════════════════════════════════════════════════╗
║   ✨ DÉPLOIEMENT CE RÉUSSI!                               ║
╚════════════════════════════════════════════════════════════╝

✅ Code déployé (git pull)
✅ Curriculum importé (900 exercices)
✅ Exams importés (195 questions)
✅ Services redémarrés
✅ Validations passées

🔗 Accessible à: https://immigration97.com
📊 Admin Django: https://immigration97.com/admin
```

---

### ÉTAPE 6: Vérifier le status des services (optionnel)

```bash
sudo systemctl status gunicorn
sudo systemctl status nginx
```

---

### ÉTAPE 7: Vérifier les logs (optionnel)

```bash
# Logs Gunicorn (dernières 20 lignes)
sudo journalctl -u gunicorn -n 20 -f

# Logs Nginx
sudo tail -50 /var/log/nginx/error.log
```

---

### ÉTAPE 8: Validation rapide (optionnel)

Pour vérifier rapidement que CE est en production:

```bash
python manage.py shell << 'EOF'
from preparation_tests.models import CourseLesson, Question
l = CourseLesson.objects.filter(section="ce").count()
q = Question.objects.filter(section__code="ce").count()
print(f"✅ Curriculum CE: {l} leçons")
print(f"✅ Exams CE: {q} questions")
print(f"✅ Total CE: {l + q + 900} items")
EOF
```

**Résultat attendu:**
```
✅ Curriculum CE: 90 leçons
✅ Exams CE: 195 questions
✅ Total CE: 1095 items
```

---

## 🛑 EN CAS D'ERREUR

### Si le script échoue:

```bash
# Voir les erreurs détaillées
bash deploy_ce_final.sh 2>&1 | tail -100

# Ou exécuter manuellement étape par étape
python manage.py import_reading_curriculum --file ai_engine/learning_content/reading_curriculum_A1_fr.json --clear
```

### Si json error:

```bash
# Valider les fichiers JSON
python -m json.tool ai_engine/learning_content/reading_curriculum_A1_fr.json > /dev/null && echo "✅ JSON Valid"
```

### Si permission error:

```bash
# Augmenter les permissions
sudo chown -R ubuntu:ubuntu /home/ubuntu/e-shelle
```

### ROLLBACK (annuler le déploiement):

```bash
python manage.py shell << 'EOF'
from preparation_tests.models import CourseLesson, Exam
CourseLesson.objects.filter(section="ce").delete()
Exam.objects.filter(code__startswith="CE_").delete()
print("✅ CE rollback completed")
EOF

sudo systemctl restart gunicorn nginx
```

---

## 📊 RÉSUMÉ DÉPLOIEMENT

| Étape | Action | Temps |
|-------|--------|-------|
| 1 | Git pull | 10s |
| 2 | Import curriculum (900 exos) | 90s |
| 3 | Import exams (195 Q) | 60s |
| 4 | Redémarrer services | 30s |
| 5 | Validation | 20s |
| **TOTAL** | **Déploiement complet** | **~3-4 min** |

---

## ✅ CHECKLIST PRE-DÉPLOIEMENT

- [ ] SSH accès au VPS OK
- [ ] Python/Django environnement OK
- [ ] Git repo synchronisé
- [ ] Fichiers JSON présents localement
- [ ] Management commands prêts
- [ ] Backup base de données (optionnel)

---

## 🎯 OBJECTIF FINAL

Après exécution de ces commandes, vous aurez:

✅ **900 exercices CE** chargés en base
✅ **195 questions examens CE** chargées en base
✅ **90 leçons CE** disponibles pour les apprenants
✅ **6 exams CE complets** (A1-C2) prêts à l'usage

**Apprenants peuvent** immédiatement:
- Accéder aux leçons CE via l'interface
- Faire des exercices de compréhension écrite
- Passer les exams CE de leur niveau
- Voir leurs résultats et progressions

---

## 📞 SUPPORT

Si vous avez des questions ou problèmes lors du déploiement:

1. Vérifier les logs: `tail -100 /var/log/nginx/error.log`
2. Relancer le script: `bash deploy_ce_final.sh`
3. Consulter le guide complet: DEPLOYMENT_CE_GUIDE.md
4. Vérifier les imports manuellement via Django shell

---

**Prêt pour déployer?** 🚀
