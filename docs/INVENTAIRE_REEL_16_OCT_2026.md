# Inventaire réel E-Shelle — état du code et limites de vérification

**Date de rédaction : 17 octobre 2026**

**Périmètre :** dépôt local `e_shelle`, sources versionnées et lecture sans écriture de la base SQLite configurée localement.

**Important :** ce document ne prétend pas être un audit connecté au VPS. L’accès SSH à `vps3581805` a été tenté en mode non interactif et a répondu `Permission denied (publickey,password)`. Aucun fichier `.env` n’a été lu ni copié. Les éléments marqués **NON VÉRIFIÉ EN PRODUCTION** ne doivent pas servir de preuve pour Meta ni pour un devis client.

Les numéros après `:L` sont les lignes du dépôt local au moment de la rédaction. Le guide commercial demandé a 7 pages; les affirmations attribuées à sa page 2 sont citées par page, car un PDF n’a pas de numérotation de lignes.

## Résumé exécutif

| Sujet | Ce que le code prouve | Ce qui n’est pas prouvé |
|---|---|---|
| WhatsApp global | Le dépôt contient l’intégration Cloud API, les tâches de campagnes, les statuts de livraison par webhook et le CRM. [whatsapp_agent/services.py:L54-L113](../whatsapp_agent/services.py#L54) [whatsapp_agent/views.py:L1138-L1176](../whatsapp_agent/views.py#L1138) | Que tous les flags, workers, secrets, migrations et webhooks soient actifs sur le VPS. |
| WhatsApp Business par PME | Le modèle et le CRM existent. Les relances par contact ont des contrôles d’activation. [whatsapp_commerce/models.py:L66-L111](../whatsapp_commerce/models.py#L66) [whatsapp_commerce/tasks.py:L70-L100](../whatsapp_commerce/tasks.py#L70) | L’envoi d’une campagne liée à une fiche Business est explicitement bloqué dans la vue de lancement. [whatsapp_agent/views.py:L680-L689](../whatsapp_agent/views.py#L680) |
| Consentement `0015` | Le code local contient une migration additive avec les champs facultatifs; elle a été créée et commitée localement dans `3ac516e`. [whatsapp_agent/migrations/0015_add_consent_fields_safe.py:L1-L39](../whatsapp_agent/migrations/0015_add_consent_fields_safe.py#L1) | Que ce commit soit poussé, déployé ou migré sur le VPS. L’authentification SSH a échoué. |
| Tarification 10 000 FCFA campagne | `Campagne.price_charged` a un défaut de `10000`. [whatsapp_agent/models.py:L57-L92](../whatsapp_agent/models.py#L57) | Un paiement de campagne, une preuve de paiement ou un envoi business disponible. |
| Snapshot des messages | La base SQLite locale renvoie 44 `en_attente` et 57 `envoye` au moment de la requête. | Le nombre courant de messages sur la base de production. |

## 1. Stack vérifiable

| Élément | Résultat vérifié | Preuve / limite |
|---|---|---|
| Projet Django | `manage.py` sélectionne `edu_cm.settings`. Le `requirements.txt` versionne `Django==6.0.2`; le shell local a également importé Django `6.0.2`. | [manage.py:L8-L18](../manage.py#L8) [requirements.txt:L17](../requirements.txt#L17). Le VPS annoncé comme Django 5 n’a pas pu être contrôlé; **la version production est NON VÉRIFIÉE**. |
| Python | `.python-version` indique `3.13.13`; le shell local interrogé a exécuté Python `3.13.14`. | [.python-version:L1](../.python-version#L1). La version Python du VPS est **NON VÉRIFIÉE**. |
| Base | Le code choisit PostgreSQL si `DATABASE_URL` est présent et que les conditions de production sont satisfaites; sinon il utilise `db.sqlite3`. | [edu_cm/settings.py:L285-L310](../edu_cm/settings.py#L285). Le shell local a rapporté `sqlite`, sans hôte distant configuré. Le moteur de production est **NON VÉRIFIÉ**. |
| Queue | Celery 5.6.3, `django-celery-beat` et Redis 7.4.0 sont dans les dépendances; le broker par défaut déclaré est Redis local. | [requirements.txt:L6,L19-L21,L47](../requirements.txt#L6) [edu_cm/settings.py:L662-L670](../edu_cm/settings.py#L662). L’existence de ces dépendances ne prouve pas que Redis, Celery worker ou Beat tourne sur le VPS. |
| Hôte | Les documents identifient le serveur cible sous le nom `vps3581805`, chemin `/home/eshelle/app`. | [docs/VPS_ENV_CHECKLIST_2026.md:L1-L4](./VPS_ENV_CHECKLIST_2026.md#L1). Le nom d’hôte courant et l’état des services sur ce serveur n’ont pas été lus. |
| Configuration `.env` | Un `.env` local existe; il n’a pas été lu. Un `.env.example` à la racine est **NON TROUVÉ**. Des exemples séparés existent dans certains sous-projets. | Recherche des chemins versionnés et test d’existence; ne pas confondre les exemples de sous-projets avec la configuration Django racine. |
| Flags de sécurité locaux | Le shell local a renvoyé `WHATSAPP_COMMERCE_ENABLED=false`, `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED=false`, `WHATSAPP_DRY_RUN=true`. | Résultat runtime local. Les défauts de code sont `False`, `False` et `True` respectivement. [edu_cm/settings.py:L632,L647-L653](../edu_cm/settings.py#L632) |
| Flags du VPS | **NON VÉRIFIÉS.** Le code lit ces variables dans l’environnement; les valeurs du `.env` VPS ne sont pas accessibles depuis cet audit. | La checklist VPS indique elle-même qu’elle ne vérifie pas les valeurs à distance. [docs/VPS_ENV_CHECKLIST_2026.md:L42-L48](./VPS_ENV_CHECKLIST_2026.md#L42) |

### Configuration WhatsApp par défaut dans le code

| Setting | Défaut déclaré | Sens |
|---|---:|---|
| `WHATSAPP_DRY_RUN` | `True` | Le code peut traiter une simulation comme succès sans appel Meta si ce réglage demeure actif. [edu_cm/settings.py:L632](../edu_cm/settings.py#L632) [whatsapp_agent/services.py:L88-L101](../whatsapp_agent/services.py#L88) |
| `WHATSAPP_COMMERCE_ENABLED` | `False` | Commerce désactivé par défaut. [edu_cm/settings.py:L647-L648](../edu_cm/settings.py#L647) |
| `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED` | `False` | Automatisations Business désactivées par défaut; la tâche de relance retourne sans envoyer lorsque le flag est faux. [edu_cm/settings.py:L649-L652](../edu_cm/settings.py#L649) [whatsapp_commerce/tasks.py:L70-L100](../whatsapp_commerce/tasks.py#L70) |
| `WHATSAPP_COMMERCE_AI_ENABLED` | `True` | Le drapeau AI a un défaut positif, mais cela ne neutralise pas le flag Commerce désactivé et ne prouve pas que les fonctions AI sont utilisées en production. [edu_cm/settings.py:L653](../edu_cm/settings.py#L653) |
| `WHATSAPP_CONFIG_READY` | Calculé depuis les credentials Meta requis | Sa valeur VPS n’a pas été lue. [edu_cm/settings.py:L631-L640](../edu_cm/settings.py#L631) |

## 2. Modèles critiques — schéma du code

Les descriptions ci-dessous sont les champs déclarés par les modèles locaux, pas une inspection du schéma PostgreSQL VPS.

### `ProviderPlan`

Champs pertinents : `code`, `name`, `name_en`, `plan_level`, `monthly_price_xaf`, `duration_days`, `included_boost_days`, **`included_ai_credits`** (pluriel dans le code, pas `included_ai_credit`), `description`, `description_en`, `is_active`, `order`. [business/models.py:L510-L529](../business/models.py#L510)

Le seeder propose les paliers 0, 5 000, 15 000 et 25 000 FCFA pour Free, Pro, Business et Premium. C’est le contenu du seeder, **pas la preuve des valeurs actuellement présentes dans la base de production**. [business/management/commands/seed_business_plans.py:L10-L55](../business/management/commands/seed_business_plans.py#L10)

### `AppPlan`

Champs de prix et d’identification : `app_key`, `slug`, `name`, `name_en`, `level`, `price_xaf`, `price_eur`, `duration_days`, `features`, `features_en`, `is_free`, `is_popular`, `is_active`, `order`, `created_at`. Il n’existe pas de champ `monthly_price` dans ce modèle; le nom utilisé est `price_xaf`. [accounts/models.py:L162-L193](../accounts/models.py#L162)

`accounts/management/commands/seed_plans.py` fournit notamment des tarifs AdGen 3 000 / 10 000 / 25 000 FCFA, Resto Trial à 0, Basic à 5 000 et Premium à 15 000. Ce sont des tarifs seedés dans le code, **pas un snapshot de la table VPS**. [accounts/management/commands/seed_plans.py:L10-L118](../accounts/management/commands/seed_plans.py#L10)

### `Campagne`

Champs déclarés : `nom`, `description`, `business`, `message_template`, `audience_interest`, `price_charged`, `template_meta_name`, `template_meta_language`, `template_meta_params`, `template_meta_preview`, `statut`, `filtre_role`, `filtre_ville`, `filtre_date_inscription_depuis`, `destinataires_contacts`, `total_destinataires`, `total_envoyes`, `total_livres`, `total_lus`, `total_echecs`, `clicked_count`, `cree_par`, `cree_le`, `lance_le`, `termine_le`. [whatsapp_agent/models.py:L57-L120](../whatsapp_agent/models.py#L57)

États de campagne déclarés : `brouillon`, `validee`, `en_cours`, `terminee`, `annulee`. [whatsapp_agent/models.py:L60-L74](../whatsapp_agent/models.py#L60)

`price_charged = IntegerField(default=10000)` est une valeur par défaut, pas un enregistrement de transaction. `Campagne` ne déclare ni relation de paiement, ni référence de transaction, ni statut de paiement. [whatsapp_agent/models.py:L87-L92](../whatsapp_agent/models.py#L87)

### `MessageEnvoi`

Champs déclarés : `campagne`, `user`, `commercial_prospect`, `destinataire_nom`, `numero_whatsapp`, `message_final`, `statut`, `whatsapp_message_id`, `erreur`, `envoye_le`, `mis_a_jour_le`. Le statut disponible est `en_attente`, `envoye`, `livre`, `lu`, `echec`. [whatsapp_agent/models.py:L169-L203](../whatsapp_agent/models.py#L169)

- Le statut littéral **`pret` n’est pas défini** par `MessageEnvoi`. Si l’interface montre « prêt », ce n’est pas l’un des choix du champ `statut` de ce modèle. [whatsapp_agent/models.py:L172-L183](../whatsapp_agent/models.py#L172)
- `mis_a_jour_le` est un `DateTimeField(auto_now=True)`; `erreur` est un champ texte. [whatsapp_agent/models.py:L198-L202](../whatsapp_agent/models.py#L198)
- `campagne__statut` est une traversée ORM vers `Campagne.statut`, pas un champ de `MessageEnvoi`. [whatsapp_agent/models.py:L186-L198](../whatsapp_agent/models.py#L186)
- Il n’y a pas de champ `contact` reliant une ligne `MessageEnvoi` au modèle `ContactWhatsApp`. Les champs destinataire associés directement sont `user`, `commercial_prospect`, le nom et le numéro. [whatsapp_agent/models.py:L186-L203](../whatsapp_agent/models.py#L186)

### Consentement et `0015`

`ContactWhatsApp` a les anciens champs `consentement_confirme`, `consentement_source`, `consentement_le`, `desinscrit`, `desinscrit_le`; le code local ajoute `consent_service`, `consent_marketing`, `consent_date`, `consent_source`, `consent_entity`. Les deux booléens ont `default=False`, `null=True`, `blank=True`; la FK Business est nullable et `SET_NULL`. [whatsapp_agent/models.py:L5-L46](../whatsapp_agent/models.py#L5)

La migration `0015_add_consent_fields_safe` est additive et dépend des migrations WhatsApp `0014` et Business `0033`. Elle n’ajoute aucun filtre d’envoi. [whatsapp_agent/migrations/0015_add_consent_fields_safe.py:L7-L39](../whatsapp_agent/migrations/0015_add_consent_fields_safe.py#L7)

Dans la préparation des campagnes à contacts sélectionnés, le code vérifie encore `consentement_confirme=True` et `desinscrit=False`; le commentaire indique le filtre marketing futur, mais celui-ci n’est pas exécuté. [whatsapp_agent/views.py:L108-L126](../whatsapp_agent/views.py#L108)

## 3. Flux WhatsApp réellement présent

### États et passage de l’envoi à la lecture

1. Une campagne globale doit être validée et confirmée dans la vue de lancement; si `WHATSAPP_DRY_RUN` est vrai, elle est traitée directement en simulation, sinon la tâche Celery est mise en file. [whatsapp_agent/views.py:L680-L717](../whatsapp_agent/views.py#L680)
2. La tâche récupère seulement les `MessageEnvoi` en `en_attente`, ordonnés par ID. [whatsapp_agent/tasks.py:L145-L176](../whatsapp_agent/tasks.py#L145)
3. `envoyer_message_task` charge le message et sa campagne, puis appelle `WhatsAppService.envoyer_message(...)`; le succès met `statut="envoye"`, l’identifiant Meta et l’heure d’envoi, l’échec final met `statut="echec"` et conserve le message d’erreur. [whatsapp_agent/tasks.py:L95-L141](../whatsapp_agent/tasks.py#L95)
4. Le webhook traduit les statuts Meta `sent`, `delivered`, `read`, `failed` en `envoye`, `livre`, `lu`, `echec`, met à jour la ligne liée par `whatsapp_message_id`, puis recalcule les compteurs de campagne. [whatsapp_agent/views.py:L1160-L1176](../whatsapp_agent/views.py#L1160)
5. L’appel HTTP sortant se fait par `requests.post(settings.WHATSAPP_API_URL, json=payload, headers=headers, timeout=10)` dans le service WhatsApp. En mode simulation, le service retourne un identifiant `dryrun-*` sans appel Meta. [whatsapp_agent/services.py:L54-L113](../whatsapp_agent/services.py#L54)

Pour le chemin texte, le corps JSON construit avant le POST est :

```json
{
  "messaging_product": "whatsapp",
  "to": "<numéro normalisé par le service>",
  "type": "text",
  "text": {"body": "<message>", "preview_url": false}
}
```

Si un template est utilisé, le corps a `type: "template"` et contient son `name`, sa `language.code` et, si nécessaire, les paramètres texte du corps. La sélection template peut être forcée par configuration; ne pas déduire qu’un envoi texte libre est autorisé hors fenêtre de service. [whatsapp_agent/services.py:L54-L113](../whatsapp_agent/services.py#L54) [whatsapp_agent/services.py:L114-L183](../whatsapp_agent/services.py#L114)

**Requête de sélection exacte de la file campagne :**

```python
campagne.messages.filter(statut=MessageEnvoi.STATUT_EN_ATTENTE).order_by("id")
```

Cette sélection apparaît dans la tâche campagne Celery; l’exécution unitaire recherche ensuite `MessageEnvoi.objects.select_related("campagne").get(id=message_envoi_id)`. [whatsapp_agent/tasks.py:L95-L97](../whatsapp_agent/tasks.py#L95) [whatsapp_agent/tasks.py:L145-L157](../whatsapp_agent/tasks.py#L145)

Pour une sélection manuelle de contacts, la préparation vérifie `destinataires_contacts.filter(consentement_confirme=True, desinscrit=False)`. Elle ne filtre pas sur le nouveau `consent_marketing`. [whatsapp_agent/views.py:L118-L127](../whatsapp_agent/views.py#L118)

### Où ça bloque

- **Campagne liée à un business :** la vue de lancement la refuse explicitement avec le message « L’envoi des campagnes liées à un business n’est pas encore disponible ». La création reste un brouillon. [whatsapp_agent/views.py:L440-L468](../whatsapp_agent/views.py#L440) [whatsapp_agent/views.py:L680-L689](../whatsapp_agent/views.py#L680)
- **Campagne globale :** il faut que son statut soit `validee`, cocher la confirmation, et satisfaire la validation du modèle Meta lorsqu’un template est associé. En mode réel, il faut aussi que Celery/Redis réponde. [whatsapp_agent/views.py:L689-L717](../whatsapp_agent/views.py#L689)
- **Consentement :** `0015` ajoute les cases/champs, mais le filtre marketing n’est pas relié au sender; `MessageEnvoi` n’a pas de FK `contact`. Il n’y a donc pas de preuve dans le code que les futures campagnes marketing ne ciblent que `consent_marketing=True`. [whatsapp_agent/views.py:L118-L126](../whatsapp_agent/views.py#L118) [whatsapp_agent/models.py:L186-L203](../whatsapp_agent/models.py#L186)
- **Production :** le code et des fichiers systemd de déploiement existent, mais l’état actif des services, les valeurs VPS des flags, l’état des migrations, les erreurs Meta et le webhook n’ont pas pu être interrogés. [deploy/eshelle-celery.service:L1-L15](../deploy/eshelle-celery.service#L1) [deploy/eshelle-celerybeat.service:L1-L15](../deploy/eshelle-celerybeat.service#L1)

### Les 637 échecs et 325 en attente rapportés pour le 16 octobre

Ces nombres et le nettoyage sont rapportés par le demandeur; **ils ne sont pas vérifiés indépendamment**. Aucune base VPS, archive d’événements, journal de purge ni export avant/après n’a été obtenu. On ne peut donc pas affirmer ce qui a créé ces lignes, si elles étaient liées à la même campagne, ni si la purge les a supprimées.

Le code contient plusieurs chemins qui peuvent produire un échec — protection contre un destinataire déjà contacté, réponse Meta non réussie, credentials absents ou erreurs réseau — mais aucun ne peut être attribué à ces 637 lignes sans leurs anciennes valeurs `erreur`, leurs campagnes et les logs correspondants. [whatsapp_agent/tasks.py:L34-L70](../whatsapp_agent/tasks.py#L34) [whatsapp_agent/tasks.py:L95-L126](../whatsapp_agent/tasks.py#L95) [whatsapp_agent/services.py:L96-L140](../whatsapp_agent/services.py#L96)

## 4. Pricing et parcours de paiement

### 10 000 FCFA campagne

- Le modèle définit `price_charged = models.IntegerField(default=10000)`. [whatsapp_agent/models.py:L86-L92](../whatsapp_agent/models.py#L86)
- La migration `0013` a également introduit le défaut `10000`. [whatsapp_agent/migrations/0013_campagne_audience_interest_campagne_business_and_more.py:L29-L35](../whatsapp_agent/migrations/0013_campagne_audience_interest_campagne_business_and_more.py#L29)
- Je n’ai trouvé aucun modèle de transaction référencé par `Campagne`; `price_charged` seul ne démontre ni encaissement, ni reçu, ni paiement d’une campagne. [whatsapp_agent/models.py:L57-L120](../whatsapp_agent/models.py#L57)
- L’envoi des campagnes avec `business_id` est bloqué comme indiqué ci-dessus. Le PDF de vente reconnaît cette limite à la **page 2**. [docs/guide-commercial-pme-whatsapp-eshelle.pdf, p. 2](./guide-commercial-pme-whatsapp-eshelle.pdf)

### CTA Academy affiché sur la page d’accueil

Le CTA est affiché comme « Rejoindre la formation WhatsApp Business — 10 000 FCFA » et pointe sur `{% url 'formation' %}`. [templates/home.html:L853-L861](../templates/home.html#L853)

`formation` correspond à `/formation/`, dont `formation_view` remplit le portail avec les formations publiées en base; cette vue ne fixe pas un cours WhatsApp particulier à 10 000 FCFA. [edu_cm/urls.py:L115-L133](../edu_cm/urls.py#L115) [edu_cm/urls.py:L936-L942](../edu_cm/urls.py#L936)

Parcours d’un **cours payant sélectionné** : l’inscription nécessite une connexion; `formations.views.inscrire` redirige vers `payments:payer_formation`; cette vue affiche l’option de paiement CamPay et une demande de paiement par WhatsApp. La route CamPay crée une transaction `achat_cours` au prix du cours et démarre le checkout. [formations/views.py:L204-L220](../formations/views.py#L204) [payments/views.py:L603-L635](../payments/views.py#L603) [payments/views.py:L313-L354](../payments/views.py#L313) [payments/urls.py:L11-L17](../payments/urls.py#L11)

**Tarif de cours WhatsApp à 10 000 et disponibilité du cours en production : NON VÉRIFIÉS.** Le CTA marketing n’est pas une preuve de tarif enregistré, de cours publié, de paiement initié ou de paiement reçu. Les cours et leurs prix sont définis en base par `Formation.prix`; le snapshot de la base du VPS n’a pas été obtenu. [formations/models.py:L30-L60](../formations/models.py#L30) [docs/guide-commercial-pme-whatsapp-eshelle.pdf, p. 2](./guide-commercial-pme-whatsapp-eshelle.pdf)

### Offre prestataire et Business Key

- Le seeder source des offres mensuelles prestataires est `seed_business_plans`: Free 0, Pro 5 000, Business 15 000, Premium 25 000 FCFA. [business/management/commands/seed_business_plans.py:L10-L55](../business/management/commands/seed_business_plans.py#L10)
- Le code déclare également Business Key à 9 900 FCFA, commission de recrutement à 50 % et commission prestataire à 30 %. [business/views.py:L53-L55](../business/views.py#L53)
- La demande Business Key est enregistrée en base et passe par validation staff avant confirmation/activation; elle n’est pas la preuve d’un encaissement automatique. [business/views.py:L1949-L1980](../business/views.py#L1949) [business/views.py:L2051-L2064](../business/views.py#L2051)
- Les prix actuels des tables `ProviderPlan`, `AppPlan` et `Formation` du VPS sont **NON VÉRIFIÉS**. Les valeurs seedées ne doivent pas être présentées comme un export des prix actifs en production.

## 5. Guides : promesses à ne pas confondre avec la production

| Énoncé de guide / marketing | État démontré par le code local | Conclusion prudente |
|---|---|---|
| Le guide commercial page 2 propose la fiche Business, les métriques et le CRM comme fonctions vendables; il indique que les campagnes business restent en brouillon et que l’envoi est bloqué. | La vue `lancer_campagne` confirme ce blocage pour toute campagne avec `business_id`. [whatsapp_agent/views.py:L680-L689](../whatsapp_agent/views.py#L680) | Présenter la fiche et le suivi selon les données/configuration réelles; ne pas vendre un envoi automatique lié au business comme déjà disponible. |
| Le même PDF précise que le montant `price_charged=10 000` n’est pas une preuve de paiement et que le CTA Academy ne prouve pas le prix du cours. | Cela correspond au modèle `Campagne` et au CTA `/formation/`. [whatsapp_agent/models.py:L87-L92](../whatsapp_agent/models.py#L87) [templates/home.html:L853-L861](../templates/home.html#L853) | Conserver ces réserves dans le pitch. |
| `whatsapp-business-mvp.md` décrit Embedded Signup, CRM et relances personnalisées, mais demande explicitement les autorisations Meta, le consentement, les modèles et les workers. | L’intégration et la tâche de relance sont dans le code; l’exécution VPS n’a pas été vérifiée. Les flags ont des défauts désactivés. [docs/whatsapp-business-mvp.md:L5-L35](./whatsapp-business-mvp.md#L5) [edu_cm/settings.py:L647-L653](../edu_cm/settings.py#L647) | La présence de code ne prouve pas la disponibilité commerciale sur le VPS. |
| Le guide du MVP dit que les campagnes de masse et les messages libres planifiés ne sont pas dans cette tranche; seules des relances individuelles par template sont prévues. | Le code distingue campagnes staff/globales et relances CRM Business; les relances ont un flag dédié et les campagnes business sont bloquées. [docs/whatsapp-business-mvp.md:L19-L25](./whatsapp-business-mvp.md#L19) [whatsapp_commerce/tasks.py:L70-L100](../whatsapp_commerce/tasks.py#L70) | Ne pas annoncer campagne business de masse disponible. |
| Le guide `VPS_ENV_CHECKLIST_2026.md` donne des valeurs souhaitées pour les flags mais précise qu’il ne lit pas les valeurs du serveur. | Le fichier est une checklist, pas un relevé d’état; le VPS n’a pas été joignable dans cet audit. [docs/VPS_ENV_CHECKLIST_2026.md:L7-L19,L42-L48](./VPS_ENV_CHECKLIST_2026.md#L7) | Valeurs réellement configurées en production : NON VÉRIFIÉES. |
| La page d’accueil dit « candidature Tech Provider en cours d’examen ». | C’est une chaîne de présentation dans le template, pas une réponse de l’API Meta ni un statut administratif contrôlé. [templates/home.html:L863-L874](../templates/home.html#L863) | Le statut actuel Meta doit être confirmé depuis le Business Manager/App Dashboard. |

### État de `0015` en production

La migration se trouve dans la branche locale au commit `3ac516e`; la présente machine n’a pas pu s’authentifier au VPS. Il est donc **impossible de certifier que le commit est déployé ou que `whatsapp_agent.0015_add_consent_fields_safe` a été appliquée**. Même appliquée, cette migration seule ne filtre pas l’envoi marketing; le code de préparation emploie encore l’ancien booléen `consentement_confirme`. [whatsapp_agent/migrations/0015_add_consent_fields_safe.py:L7-L39](../whatsapp_agent/migrations/0015_add_consent_fields_safe.py#L7) [whatsapp_agent/views.py:L118-L126](../whatsapp_agent/views.py#L118)

## 6. Snapshot brut des messages

### Production

**NON OBTENU.** L’accès SSH au VPS a répondu `Permission denied (publickey,password)`. Aucun ORM Django n’a été exécuté sur la base VPS; aucun nombre ci-dessous ne doit être interprété comme le snapshot de production.

### SQLite locale (exécution effectuée, explicitement non-production)

La requête ORM exécutée dans le shell local était :

```python
MessageEnvoi.objects.values("statut").annotate(count=Count("id")).order_by("statut")
```

Résultat JSON brut du runtime local :

```json
{
  "python": "3.13.14",
  "django": "6.0.2",
  "database_vendor": "sqlite",
  "database_remote_host_configured": false,
  "message_counts_by_status": [
    {"statut": "en_attente", "count": 44},
    {"statut": "envoye", "count": 57}
  ],
  "whatsapp_commerce_enabled": false,
  "whatsapp_business_automations_enabled": false,
  "whatsapp_dry_run": true
}
```

Ce résultat local ne confirme ni les nombres de production, ni les nombres annoncés de Campagne 55 (`Total 4 / Envoyés 4 / Livrés 2 / Lu 1 / Échecs 0`), ni le nettoyage rapporté de 637 échecs et 325 attentes le 16 octobre. Ces deux dernières informations proviennent de la demande utilisateur, pas d’une lecture de la base VPS.

## 7. Trois blocages de revenus — preuves du code uniquement

1. **L’offre de campagne à 10 000 FCFA n’a pas le parcours de vente complet.** Le modèle porte un prix par défaut, mais aucune transaction/preuve de paiement; de plus, le lancement bloque les campagnes rattachées à un business. Le montant ne peut donc pas être présenté comme une vente de campagne automatisée déjà opérationnelle. [whatsapp_agent/models.py:L87-L92](../whatsapp_agent/models.py#L87) [whatsapp_agent/views.py:L680-L689](../whatsapp_agent/views.py#L680)
2. **Les automatisations WhatsApp Business sont opt-in côté configuration et la production n’est pas vérifiée.** Le défaut est désactivé, la tâche vérifie ce flag avant d’envoyer, et aucun accès opérationnel au VPS n’a confirmé son état ou celui des workers. [edu_cm/settings.py:L649-L652](../edu_cm/settings.py#L649) [whatsapp_commerce/tasks.py:L70-L100](../whatsapp_commerce/tasks.py#L70) [docs/VPS_ENV_CHECKLIST_2026.md:L42-L48](./VPS_ENV_CHECKLIST_2026.md#L42)
3. **Le nouveau consentement marketing n’est pas imposé par l’envoi des campagnes.** La préparation retient l’ancien champ `consentement_confirme`; le nouveau `consent_marketing` est seulement commenté comme filtre futur et `MessageEnvoi` n’a pas de lien vers le contact pour le contrôler à l’envoi. C’est un blocage technique et de conformité avant de vendre l’audience PME. [whatsapp_agent/views.py:L118-L126](../whatsapp_agent/views.py#L118) [whatsapp_agent/models.py:L186-L203](../whatsapp_agent/models.py#L186)

## 8. Tâches, Beat et commandes recensées

### Scheduler Celery Beat déclaré dans le dépôt

Le dépôt définit **43 entrées** dans `edu_cm/celery.py`. Ce tableau décrit la configuration du code; il ne prouve pas que Celery Beat tourne sur le VPS. [edu_cm/celery.py:L27-L274](../edu_cm/celery.py#L27)

| Famille | Entrées Beat et rythme déclaré |
|---|---|
| OCR | `phone-ocr-cleanup` toutes les 600 s. [edu_cm/celery.py:L29-L31](../edu_cm/celery.py#L29) |
| Publications Facebook | Annonces 09:00, 14:00, 20:00; immobilier 10:30; auto 11:00; agro 07:30; rencontres 08:00 et 21:00; Njangi 18:00; promo lun/mer/ven 12:00; général 19:00; chat IA 08:30; gaz 07:00 et 21:00; resto 11:30; pressing 07:45; santé 19:30; jobs 15:00; business 18:30. [edu_cm/celery.py:L33-L144](../edu_cm/celery.py#L33) |
| Maintenance Facebook | Publications planifiées toutes les 5 min; stats toutes les 6 h; validation token à 06:00; mise à jour stats à chaque heure à :30. [edu_cm/celery.py:L146-L169](../edu_cm/celery.py#L146) |
| Njangi | Intérêts le 1er du mois à 02:00; pénalités chaque jour à 06:30; défauts de prêt à 07:30; score le dimanche à 03:00. [edu_cm/celery.py:L172-L195](../edu_cm/celery.py#L172) |
| Offres Allemagne | Nettoyage à 01:00, 09:00, 17:00; recherche quotidienne 06:00; enrichissement IA 06:30. [edu_cm/celery.py:L197-L209](../edu_cm/celery.py#L197) |
| GermanPrepApp | Catalogue 06:45; contenu 07:05; placement 07:35; audio 07:55; examens blancs 08:10. [edu_cm/celery.py:L210-L235](../edu_cm/celery.py#L210) |
| Canada | Offres emplois 03:30; bourses 06:45; opportunités visiteurs 07:00; actualités 07:15. [edu_cm/celery.py:L237-L258](../edu_cm/celery.py#L237) |
| Business | Rappels d’expiration 08:00; downgrade 08:15; relances WhatsApp Business chaque minute. [edu_cm/celery.py:L260-L274](../edu_cm/celery.py#L260) |

Les services systemd worker et Beat existent dans `deploy/`; leur état actif sur le VPS est **NON VÉRIFIÉ**. [deploy/eshelle-celery.service:L1-L15](../deploy/eshelle-celery.service#L1) [deploy/eshelle-celerybeat.service:L1-L15](../deploy/eshelle-celerybeat.service#L1)

Un script de déploiement installe aussi un cron système pour `certbot renew` à 03:00. Cela prouve l’intention du script, pas le contenu actuel de `crontab -l` sur le serveur. [deploy/deploy.sh:L158-L160](../deploy/deploy.sh#L158)

### Fonctions de tâches Celery identifiées dans les fichiers projet

- `whatsapp_agent.tasks`: `envoyer_message_task`, `lancer_campagne_task`. [whatsapp_agent/tasks.py:L95-L176](../whatsapp_agent/tasks.py#L95)
- `whatsapp_commerce.tasks`: `process_due_business_whatsapp_follow_ups`; le fichier contient aussi la logique de vérification des paniers abandonnés. [whatsapp_commerce/tasks.py:L1-L100](../whatsapp_commerce/tasks.py#L1)
- `business.tasks`: `remind_expiring_businesses`, `downgrade_expired_businesses`. [business/tasks.py:L10-L90](../business/tasks.py#L10)
- `facebook_agent.tasks`: `generate_and_publish_post`, `publish_scheduled_post`, `process_pending_scheduled_posts`, `sync_post_stats`, `update_daily_stats`, `check_token_validity`. [facebook_agent/tasks.py:L20-L374](../facebook_agent/tasks.py#L20)
- `phone_ocr_agent.tasks`: `process_ocr_job`, `cleanup_ocr_jobs`. [phone_ocr_agent/tasks.py:L28-L53](../phone_ocr_agent/tasks.py#L28)
- `njangi.tasks`: `calculate_monthly_interests_all`, `apply_penalties_all`, `check_loan_defaults`, `update_reliability_scores`, `calculate_monthly_interests_group`. [njangi/tasks.py:L16-L145](../njangi/tasks.py#L16)
- `jobs.tasks`: `fetch_canada_jobs_task`, `fetch_canada_scholarships_task`, `fetch_canada_visitor_opps_task`, `fetch_canada_news_task`. [jobs/tasks.py:L7-L55](../jobs/tasks.py#L7)
- `germany_opportunities.tasks`: `fetch_ausbildung_offers`, `enrich_offers_with_ai`, `clean_expired_germany`. [germany_opportunities/tasks.py:L78-L318](../germany_opportunities/tasks.py#L78)
- `GermanPrepApp.tasks`: `ensure_german_exam_catalog`, `generate_german_learning_content`, `generate_german_placement_questions`, `generate_german_horen_audio`, `generate_german_mock_exams`. [GermanPrepApp/tasks.py:L59-L166](../GermanPrepApp/tasks.py#L59)
- `apps/tibo/tasks/sync.py`: `sync_shopify_products`, `sync_amazon_prices`, `send_order_email`, `cleanup_old_carts`. Le code actuel de `send_order_email` renvoie `sent: False`, ce n’est pas une preuve d’envoi d’email. [apps/tibo/tasks/sync.py:L6-L23](../apps/tibo/tasks/sync.py#L6)
- `tchaslucpay/notifications.tasks`: `send_sms_notification`, `send_email_notification`. [tchaslucpay/notifications/tasks.py:L72-L100](../tchaslucpay/notifications/tasks.py#L72)
- `edu_cm.celery` et `tchaslucpay.core.celery` déclarent également chacun `debug_task`; ces tâches de diagnostic ne sont pas une preuve d’automatisation métier. [edu_cm/celery.py:L22-L24](../edu_cm/celery.py#L22) [tchaslucpay/core/celery.py:L11-L13](../tchaslucpay/core/celery.py#L11)

Les tâches déclarées dans ces modules ne sont pas nécessairement planifiées ni exécutées. La liste Beat ci-dessus est la preuve des seules entrées périodiques configurées dans le dépôt; leur état réel sur le VPS demeure **NON VÉRIFIÉ**.

### Management commands du projet suivies par Git

**98 commandes** suivies hors dépendances installées et hors `__init__.py`. Inventaire extrait des chemins versionnés; le code doit être inspecté avant d’exécuter une commande, car plusieurs commandes seed/import/cleanup modifient des données.

| App | Commandes |
|---|---|
| EnglishPrepApp | `import_english_content` |
| GermanPrepApp | `generate_german_audio`, `generate_german_content`, `generate_german_mock_exams`, `generate_german_placement`, `import_german_lessons`, `import_german_placement` |
| accounts | `compile_translations`, `promote_admin`, `seed_plans` |
| adgen | `adgen_init_modules`, `process_studio_renders`, `studio_economics` |
| agro | `seed_agro_demo`, `seed_categories`, `seed_demo` |
| ai_engine | `check_content_generation` |
| annonces_cam | `seed_market_demo` |
| apps/tibo | `clear_old_data`, `import_products`, `seed_tibo_demo`, `sync_amazon`, `sync_shopify` |
| artisans | `seed_artisans_demo` |
| artist_hub | `init_casting_session` |
| auto_cameroun | `seed_auto_demo` |
| auto_ecole | `seed_autoecole_demo` |
| billing | `create_plans`, `test_complete_tx` |
| business | `expire_business_plans`, `normalize_eshelle_urls`, `seed_app_commissions`, `seed_business_plans`, `seed_demo_prestataires`, `send_weekly_business_reports` |
| commercial_agent | `seed_commercial_agent`, `source_restaurants` |
| edu_platform | `cleanup_expired_subscriptions`, `export_subscribers`, `generate_test_code` |
| facebook_agent | `seed_facebook_marketing`, `setup_facebook_page` |
| formations | `seed_categories` |
| gaz | `seed_gaz` |
| germany_opportunities | `audit_germany_daily`, `check_germany_generation`, `clean_expired_germany` |
| immobilier_cameroun | `seed_immo_demo` |
| italian_courses | `import_lessons` |
| jobs | `audit_canada_daily`, `clean_expired_canada_jobs`, `fetch_canada_jobs`, `fetch_canada_news`, `fetch_canada_scholarships`, `fetch_canada_visitor_opps`, `seed_jobs`, `verify_links_and_deadlines` |
| math_cm | `generate_cours`, `generate_exercices`, `import_content`, `setup_classes` |
| njangi | `calculate_monthly_interests`, `seed_njangi`, `seed_njangi_demo` |
| pharma | `seed_pharma` |
| preparation_tests | `audit_learning_materials`, `clean_tcf_content`, `fix_co_audio`, `generate_exercise_audio`, `generate_tcf_content`, `import_exam_pdf`, `import_exams`, `import_french_lessons`, `import_listening_curriculum`, `import_reading_curriculum`, `import_reading_exams`, `import_writing_curriculum`, `import_writing_exams`, `prepare_tcf_daily_audio`, `repair_french_encoding`, `repair_reading_documents`, `seed_tcf_advanced_content`, `seed_tcf_mock_questions`, `setup_french_exams`, `test_tts_prod` |
| pressing | `seed_pressing` |
| rencontres | `check_love_production`, `seed_love_demo` |
| resto | `backfill_resto_subscriptions`, `seed_resto` |
| salonhub | `seed_demo` |
| sante | `import_sante_products`, `seed_sante` |
| simplo | `seed_simplo` |
| tchaslucpay | `seed_tchaslucpay` |
| transport_core | `seed_transport` |
| whatsapp_agent | `check_whatsapp_delivery`, `seed_whatsapp_contacts` |

The command inventory is based on tracked paths from the local Git checkout, not an installed-command listing from the VPS. Management commands relevant to operational checks or sales data do not themselves establish that their operations have been run.

## 9. Sources inspected

- **PDFs in `docs/`:** 10 files; text was scanned for WhatsApp, Meta, campaign, payment, commission, activation, VPS and headline price claims. The requested `guide-commercial-pme-whatsapp-eshelle.pdf` has 7 pages; its page 2 is the requested ground-truth reference.
- **Markdown files in `docs/`:** the 33 Markdown files present before creating this inventory were inventoried; claims relevant to WhatsApp, VPS configuration, pricing, activation and campaign availability were cross-checked against source. Important references include `whatsapp-business-mvp.md`, `whatsapp-production.md`, `whatsapp-files-2026.md`, `VPS_ENV_CHECKLIST_2026.md`, `hostinger-deployment-audit.md` and `etat-projet-business-key.md`.
- **Runtime/configuration:** `manage.py`, `.python-version`, `requirements.txt`, `edu_cm/settings.py`, `edu_cm/celery.py`; the actual `.env` contents were deliberately not displayed.
- **Source/data model:** `whatsapp_agent/models.py`, `whatsapp_agent/tasks.py`, `whatsapp_agent/views.py`, `whatsapp_agent/services.py`, the `0015` migration, Business/Account plan models and seed commands, formation routes and payment views.

## Conclusion honnête pour le pitch Bafoussam / Meta

Le code prouve une vitrine Business, un catalogue, des événements/compteurs, un CRM WhatsApp, une intégration d’envoi global staff et des statuts de livraison par webhook. Il ne prouve pas qu’une PME peut déjà payer 10 000 FCFA pour lancer sa propre campagne depuis sa fiche : ce parcours est explicitement bloqué. Le consentement ajouté par `0015` n’est pas encore appliqué au filtre de l’envoi. Les flags de commerce/automatisations sont désactivés par défaut; leur état en production, le worker, Beat, le schéma déployé, les prix actifs et le nombre de messages VPS restent à confirmer côté serveur.

Pour un pitch honnête, présenter les offres comme « disponibles dans le code » uniquement lorsqu’elles sont activées et démontrables sur le VPS; présenter les campagnes Business, le tarif réel de la formation et le snapshot de production comme **à vérifier/activer**, pas comme des revenus déjà réalisés.
