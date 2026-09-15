# Phone OCR : vidéos jusqu’à 200 Mo et traitement en arrière-plan

## Fonctionnement

- Limite cumulée des fichiers : 200 × 1024 × 1024 octets, contrôlée dans le navigateur et Django.
- Nginx autorise 205M sur `/phone-ocr/` pour laisser une marge au formulaire multipart.
- Celery analyse images et vidéos ; la page consulte l’état toutes les trois secondes.
- Les résultats sont liés à la session du navigateur. Le lien permet de revenir à l’analyse depuis cette session.
- L’import et la création de campagne réutilisent les résultats sans renvoyer la vidéo.
- Les fichiers sont dans `var/phone_ocr/`, hors du dossier public media. Gunicorn et Celery doivent partager ce dossier et le même utilisateur système.
- Les fichiers sont supprimés après traitement. Celery Beat nettoie les tâches abandonnées après deux heures et supprime les résultats après 24 heures.
- Une analyse est limitée à une heure ; les vidéos trop longues doivent être découpées.

## Activation sur le VPS

Transférer les changements de `phone_ocr_agent/`, `edu_cm/celery.py` et le bloc Nginx `/phone-ocr/` de `deploy/nginx.conf`. Préserver les autres modifications locales et les réglages actifs du serveur.

Depuis `/home/eshelle/app` :

```bash
sudo -u eshelle .venv/bin/python manage.py migrate phone_ocr_agent
sudo -u eshelle mkdir -p var/phone_ocr
sudo chmod 700 var/phone_ocr
sudo -u eshelle .venv/bin/python manage.py check
```

Ajouter les blocs `location /phone-ocr/` et `location @phone_ocr_too_large` au serveur HTTPS de `e-shelle.com` dans la configuration Nginx active, après sauvegarde. Ne pas remplacer toute la configuration du serveur sans comparaison.

```bash
sudo nginx -t
sudo systemctl restart eshelle-celery eshelle-celerybeat
sudo systemctl restart eshelle
sudo systemctl reload nginx
sudo systemctl is-active eshelle eshelle-celery eshelle-celerybeat redis-server
```

Vérifier les dépendances OCR : Tesseract avec langues eng/fra, MoviePy compatible avec `moviepy.editor`, et ffmpeg. Redis et les services Celery doivent fonctionner. Aucun changement de la limite mémoire Django n’est nécessaire : les fichiers volumineux sont écrits sur disque par le gestionnaire d’upload Django.

## Vérification

```powershell
.\.venv\Scripts\python.exe manage.py test phone_ocr_agent --settings=phone_ocr_agent.test_settings --noinput
```

Sur le site : envoyer une vidéo lisible de plus de 55 Mo et de moins de 200 Mo ; observer En attente, En cours puis les résultats. Recharger pendant l’analyse. Vérifier qu’une sélection de plus de 200 Mo est bloquée avant l’envoi. Tester l’import des résultats sans sélectionner de nouveau fichier.
