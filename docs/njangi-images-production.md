# Images Njangi en production

Les deux illustrations générées pour Njangi sont livrées dans `njangi/static/njangi/img/` et doivent être incluses dans le commit. Elles sont utilisées par les pages d'accueil, de création et de détail. Aucun transfert vers `media/` n'est nécessaire.

Depuis le VPS :

```bash
set -e
cd /home/eshelle/app
sudo -u eshelle git pull --ff-only origin main
sudo -u eshelle .venv/bin/python manage.py check
sudo -u eshelle .venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart eshelle
sudo systemctl is-active eshelle
curl --fail --silent --show-error --output /dev/null --write-out 'Tontine : HTTP %{http_code}\n' https://e-shelle.com/static/njangi/img/reunion-africaine-v1.webp
curl --fail --silent --show-error --output /dev/null --write-out 'Etudiants : HTTP %{http_code}\n' https://e-shelle.com/static/njangi/img/association-etudiante-v1.webp
```

Les deux URL doivent répondre HTTP 200. Vérifier ensuite `/njangi/`, `/njangi/groupe/creer/` et la fiche d'une réunion. Les dimensions explicites réservent l'espace des images sur mobile et ordinateur ; le format WebP limite le poids total à environ 386 Kio.
