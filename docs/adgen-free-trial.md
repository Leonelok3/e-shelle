# Essai gratuit AdGen

Chaque utilisateur connecté sans abonnement payant actif dispose de trois générations au total, sans renouvellement mensuel. Une génération de textes, une voix-off, une ambiance ou un montage photo consomme une utilisation. Les voix-off gratuites sont limitées à 1 000 caractères par génération. Les montages gardent les limites existantes du Studio.

Les réservations en cours comptent immédiatement dans le quota, avec verrouillage du compte en base. Une réservation restituée libère un essai ; les échecs fournisseurs incertains restent comptés selon le comportement existant du Studio. Les consultations et téléchargements restent accessibles après épuisement des essais. Une suppression de campagne ne supprime pas son utilisation.

Les abonnements payants conservent leurs quotas ; les essais ne les réduisent pas. Les administrateurs restent exemptés. Les comptes existants sans abonnement bénéficient également des trois essais : les anciennes utilisations ne sont pas marquées comme gratuites rétroactivement.

## Activation après transfert du code

```bash
cd /home/eshelle/app
source .venv/bin/activate
python manage.py migrate adgen
python manage.py check
systemctl restart eshelle eshelle-celery
```

Aucun changement Nginx ni création de forfait gratuit dans accounts n’est nécessaire. L’accès `/pub/` demande une connexion ; la page des offres propose un lien vers l’essai. La quatrième génération demande de choisir un abonnement. Tester avec un compte non administrateur.

## Tests

```powershell
.\.venv\Scripts\python.exe manage.py test adgen.test_trial adgen.test_studio --settings=adgen.test_settings --noinput
```
