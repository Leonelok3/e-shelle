# Nettoyage des offres Espace Canada

Le contrôle déterministe ne nécessite aucune clé IA. Il supprime uniquement les offres avec date complète dépassée, HTTP 404/410 ou message explicite de retrait sur le site officiel. Les erreurs temporaires et pages non reconnues sont masquées, conservées et revérifiées au prochain passage. Les offres confirmées valides sont réactivées. Le contrôle couvre aussi les offres déjà inactives.

Simulation sans écriture :

```bash
cd /home/eshelle/app
.venv/bin/python manage.py clean_expired_canada_jobs --dry-run
```

Après copie des fichiers modifiés sur le serveur, conserver une sauvegarde avant le premier nettoyage :

```bash
sudo -u eshelle .venv/bin/python manage.py dumpdata jobs.CanadaJobOffer --output /home/eshelle/canada-jobs-before-cleanup.json
sudo cp deploy/eshelle-canada-cleanup.service deploy/eshelle-canada-cleanup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now eshelle-canada-cleanup.timer
sudo systemctl start eshelle-canada-cleanup.service
sudo journalctl -u eshelle-canada-cleanup.service -n 50 --no-pager
sudo systemctl list-timers eshelle-canada-cleanup.timer
```

Le service s'exécute à nouveau une heure après la fin du passage précédent, sans chevauchement entre ses propres exécutions. Adapter utilisateur et chemin si la production utilise une autre installation. Recharger le service web après modification de la vue.

L'import utilise le même contrôle avant publication. La commande quotidienne existante appelle également ce nettoyage. La vue masque immédiatement les dates limites dépassées entre deux passages. Un retrait sur le site source reste détecté au prochain contrôle, pas instantanément.
