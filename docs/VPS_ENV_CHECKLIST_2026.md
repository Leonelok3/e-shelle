# Vérification des variables WhatsApp en production — 8 octobre 2026

Cette checklist concerne `vps3581805` (`/home/eshelle/app`). Elle ne modifie ni
`edu_cm/settings.py`, ni l'environnement du serveur.

## Variables à contrôler

Les valeurs souhaitées après validation Meta et vérification opérationnelle sont :

```dotenv
WHATSAPP_COMMERCE_ENABLED=True
WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=True
WHATSAPP_DRY_RUN=False
```

**Ne pas activer ces valeurs uniquement pour la revue Meta.** Garder les fonctions
désactivées tant que l'approbation et les permissions Meta, le WABA de test,
webhook signé, worker Celery/Beat, modèles approuvés, consentements et test de
livraison n'ont pas été vérifiés. `WHATSAPP_DRY_RUN=False` permet des envois réels :
tester seulement avec un destinataire autorisé et consentant. Les frais Meta
peuvent s'appliquer.

Ne pas afficher ni copier le contenu complet de `.env` dans un ticket ou une
conversation : il peut contenir des secrets d'API. Cette commande ne montre que
les trois flags ci-dessus :

```bash
grep -E '^(WHATSAPP_COMMERCE_ENABLED|WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED|WHATSAPP_DRY_RUN)=' /home/eshelle/app/.env
```

## Vérifications de services

```bash
sudo systemctl status eshelle --no-pager
sudo systemctl status celery --no-pager
```

Le nom de l'unité Celery peut différer sur ce VPS. Si `celery` n'existe pas,
identifier l'unité réelle avec `systemctl list-units --type=service | grep -i celery`
et vérifier aussi l'ordonnanceur Celery Beat s'il s'agit d'une unité distincte.

Cette documentation ne vérifie pas à distance les valeurs actuellement définies
sur le serveur. Après toute modification manuelle de l'environnement, redémarrer
uniquement les services concernés selon la procédure d'exploitation, puis refaire
les contrôles et un test réel contrôlé.
