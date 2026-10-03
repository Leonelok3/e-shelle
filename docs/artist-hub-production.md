# Déploiement Artist Hub sur le VPS E-Shelle existant

Depuis PowerShell, à la racine du dépôt local :

```powershell
git push origin main
```

Depuis votre session SSH sur le VPS existant (application dans
`/home/eshelle/app`, service `eshelle`) :

```bash
set -euo pipefail
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
sudo -u eshelle .venv/bin/python -m pip install -r requirements.txt
sudo -u eshelle .venv/bin/python manage.py check
sudo -u eshelle .venv/bin/python manage.py makemigrations artist_hub --check --dry-run

# Sauvegarde logique avant migration, avec les permissions du propriétaire.
sudo -u eshelle mkdir -p /home/eshelle/backups/artist-hub
backup_file="/home/eshelle/backups/artist-hub/database-$(date +%Y%m%d-%H%M%S).json"
sudo -u eshelle touch "$backup_file"
sudo chmod 600 "$backup_file"
sudo -u eshelle .venv/bin/python manage.py dumpdata --all --output "$backup_file"

sudo -u eshelle .venv/bin/python manage.py migrate --noinput
sudo -u eshelle .venv/bin/python manage.py init_casting_session
sudo -u eshelle .venv/bin/python manage.py collectstatic --noinput
sudo bash deploy/publish_artist_hub_static.sh
sudo -u eshelle .venv/bin/python manage.py showmigrations artist_hub
sudo systemctl restart eshelle
sudo systemctl is-active eshelle
curl --fail --show-error --location --output /dev/null https://e-shelle.com/artist-hub/
```

Les commandes Django doivent utiliser les mêmes variables et la même base que
le service. Le projet charge son `.env` ; vérifier ce contexte avant exécution.
La sauvegarde JSON contient des données personnelles : la conserver privée.
Une sauvegarde native PostgreSQL reste préférable pour une restauration complète.

Le casting est gratuit. Les migrations `0003` et `0004` mettent les frais à zéro
et confirment les anciens dossiers en attente, sans modifier les décisions du
jury ni supprimer l’historique financier. Les nouvelles candidatures ne créent
aucun paiement. Les routes publiques de paiement Artist Hub sont désactivées.

## Liens après déploiement

- Accueil : https://e-shelle.com/artist-hub/
- Inscription : https://e-shelle.com/artist-hub/inscription/
- Suivi : https://e-shelle.com/artist-hub/suivi/
- Dashboard staff : https://e-shelle.com/artist-hub/staff/dashboard/
- Administration : https://e-shelle.com/admin/

La commande d'initialisation fixe les nouvelles sessions au **13 novembre 2026
à 23:59:59, heure de Douala**. Pour prolonger et réactiver la session existante :

```bash
sudo -u eshelle .venv/bin/python manage.py init_casting_session --extend-registration
```

Sans cette option, une session existante reste inchangée.

Vérifier l’inscription gratuite, la confirmation, les décisions staff, le suivi et le téléchargement PDF. Booking et ticketing sont des squelettes
de modules ; les routes livrées couvrent le casting gratuit.

En cas d'échec du service :

```bash
sudo journalctl -u eshelle -n 100 --no-pager
```

Le casting a lieu le 14 novembre 2026 ; le défilé le 26 décembre 2026. La migration du calendrier met à jour la session officielle existante.
