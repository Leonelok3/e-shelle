# Disponibilité de l'espace allemand

Les offres dont la date de début est dépassée (règle déjà appliquée par le catalogue) ou non revues depuis sept jours sont masquées. Les bourses dont l'échéance est passée ou absente sont masquées. La date du jour reste incluse, dans le fuseau Django. Le filtre s'applique au catalogue, aux détails, aux offres similaires, aux favoris et aux compteurs des entreprises.

La désactivation conserve les offres, les favoris et les candidatures. Aucune migration n'est nécessaire. Les anciennes suppressions déjà effectuées ne sont pas restaurées.

Le contrôle Celery se déclenche à 01 h, 09 h et 17 h dans le fuseau de Celery (Africa/Douala en production). Il vérifie aussi les retraits explicites sur les domaines officiels arbeitsagentur.de, daad.de et goethe.de. Une erreur réseau ne constitue pas une preuve d'expiration. Les sites employeurs tiers et les pages dynamiques sans preuve de retrait ne sont pas validés par ce contrôle ; les dates et la fraîcheur de l'import restent les critères de visibilité. Aucun contrôle périodique ne détecte instantanément tous les retraits.

La collecte Ausbildung existante est conservée. Un échec complet des recherches produit désormais une erreur. Les générateurs de cours, examens, audio et la banque de secours restent inchangés. Aucun importeur de bourses DAAD n'existe actuellement : ajouter une collecte de nouveaux cycles de bourses nécessite une source exploitable et vérifiée.

Après mise à jour du code et redémarrage des services web, Celery et Beat :

```bash
sudo -u eshelle .venv/bin/python manage.py clean_expired_germany --dry-run
sudo -u eshelle .venv/bin/python manage.py clean_expired_germany --check-links
sudo -u eshelle .venv/bin/python manage.py audit_germany_daily
```

Pour exercer les générations existantes en production (requêtes source et IA réelles) :

```bash
sudo -u eshelle .venv/bin/python -u manage.py check_germany_generation > /tmp/germany-generation-check.log 2>&1
echo "Code de sortie : $?"
tail -n 80 /tmp/germany-generation-check.log
```

Lire les sorties par étape ; la présence d'un contenu existant ne prouve pas que toutes les générations IA ont réussi.
