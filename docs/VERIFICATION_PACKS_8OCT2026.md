# Vérification des packs et pages publiques — 8 octobre 2026

## Portée et résultat

Audit en lecture seule du checkout local sur `main`, commit `ca5e8ae`, avec les
prix de production fournis par le propriétaire :

| Code plan en base VPS | Prix annoncé comme vérifié |
|---|---:|
| `free` | 0 XAF |
| `pro` | 5 000 XAF |
| `business` | 15 000 XAF |
| `premium` | 25 000 XAF |

Empire (35 000 XAF) et Écosystème (60 000 XAF) sont des propositions sur devis
avec activation manuelle, pas des ProviderPlan automatiques du code.

**Verdict : NON CONFORME au texte de référence pour les pages d’offres publiques.**
La route `/business/plans/` utilise les ProviderPlan de la base, mais la page
historique `/tarifs/` affiche encore Business à 10 000 XAF. Aucune des deux pages
n’expose toutes les limites WhatsApp requises ni la note de prudence complète.
La route dédiée `/services/whatsapp-business/` n’a pas été trouvée.

Le présent audit local ne réalise aucun appel HTTP au VPS/site public. Les statuts
« OK » ci-dessous signifient que le contenu ou la route a été vérifié dans le dépôt,
pas qu’une disponibilité en production a été testée en direct.

## Fichiers vérifiés

### Chemins demandés

| Chemin recherché | Résultat |
|---|---|
| `templates/business/plans.html` | Absent |
| `templates/services/whatsapp.html` | Absent |
| `templates/services/whatsapp-business.html` | Absent |
| `business/templates/business/plans.html` | Absent |
| `templates/plans.html` | Absent |
| `e_shelle/templates/base.html` | Absent. Le template global présent est `templates/base.html`. |

### Surfaces réellement trouvées

| Fichier / route | Constat |
|---|---|
| `templates/tarifs.html` — `/tarifs/` | Page de prix statique. Les tarifs Pro et Premium concordent ; Business est périmé à 10 000 XAF. |
| `business/templates/business/provider_plans.html` — `/business/plans/` | Page dynamique alimentée par les ProviderPlan actifs. Le prix Business devrait provenir de la base à 15 000 XAF ; la vue exige toutefois une vérification du contenu réellement rendu en production. |
| `business/urls.py` | Déclare `path("plans/", views.provider_plans, name="provider_plans")`. Le préfixe `/business/` est monté depuis `edu_cm/urls.py`. |
| `templates/base.html` | Footer global avec adresses, IDs et liens légaux. |
| `templates/services/contact.html` | Coordonnées de contact complètes. |
| `templates/privacy_policy.html` | Politique de confidentialité publique liée à WhatsApp. |
| `templates/terms_of_service.html` | Conditions de service publiques. |
| `templates/about_us.html` | Présentation publique avec statut Meta formulé comme soumis à examen. |
| `edu_cm/urls.py`, `business/urls.py`, `services/urls.py` | Routes légales, plans, contact et absence de route WhatsApp Business dédiée vérifiées. |
| `templates/accounts/upgrade.html`, `templates/payments/premium_marketplace.html` | Offres d’autres applications ; à ne pas confondre avec les forfaits Business/WABA. « Annonces illimitées » concerne un pack marketplace, pas un quota WhatsApp ni le catalogue Business. |

## Prix trouvés vs attendus

| Surface | Prix trouvé dans le template | Prix/règle attendue | Résultat |
|---|---|---|---|
| `/tarifs/` — Gratuit | La section affiche un plan gratuit ; pas de montant payé affiché dans l’extrait vérifié. | 0 XAF | Pas de divergence tarifaire payante constatée. |
| `/tarifs/` — Fiche Business Premium (Pro) | 5 000 FCFA/mois | Présence/Pro : 5 000 XAF/mois | Montant conforme ; nom commercial différent du texte de référence. |
| `/tarifs/` — Plan Business | **10 000 FCFA/mois**, y compris dans le lien d’activation WhatsApp | Croissance/Business : **15 000 XAF/mois** | **KO — prix périmé**, à corriger dans ce template avant publication de l’offre. |
| `/tarifs/` — Plan Premium | 25 000 FCFA/mois, y compris dans le lien d’activation | Premium : 25 000 XAF/mois | Montant conforme. |
| `/business/plans/` — ProviderPlan | Le template affiche `plan.monthly_price_xaf` dynamiquement ; la page doit refléter la base VPS, fournie comme Gratuit 0, Pro 5 000, Business 15 000, Premium 25 000. | 0 / 5 000 / 15 000 / 25 000 XAF | **Conforme sous réserve** de confirmer le rendu HTTP de la production. |
| Empire | Non trouvé sur les pages de plans réelles relevées | 35 000 XAF, sur devis/activation manuelle | **Absent de la grille du site**. |
| Écosystème | Non trouvé sur les pages de plans réelles relevées | 60 000 XAF, sur devis/activation manuelle | **Absent de la grille du site**. |

La page `/tarifs/` est statique et n’est pas automatiquement alignée sur le seed ou
la base ProviderPlan. Tant qu’elle reste accessible comme page commerciale, son
prix Business crée une incohérence avec le prix réel du VPS.

La page `/business/plans/` affiche « Paiement mobile (Orange Money / MTN MoMo) » et
« activation en moins de 24h », puis précise « Paiement sécurisé par WhatsApp » et
« Activation manuelle sous 24h ». Le parcours de demande Business vérifié dans le
code redirige vers WhatsApp pour validation manuelle ; il ne s’agit donc pas d’une
preuve de checkout opérateur automatique. Recommandation : remplacer le résumé
ambigu par **« Paiement Mobile Money confirmé manuellement via WhatsApp. Activation
après validation du paiement. »** Ne pas annoncer un paiement automatique.

## Vérification des libellés interdits

Recherche insensible à la casse dans les templates du site pour :

- « produits illimités » ;
- « messages illimités » ;
- « utilisateurs illimités » ;
- « tout l’écosystème inclus automatiquement » ;
- « Partenaire Officiel Meta vérifié » ;
- « Premier Tech Provider » ;
- « Paiement MoMo automatique ».

**Résultat : aucun de ces libellés exacts n’a été trouvé dans les templates
inspectés.** La mention indépendante « Annonces illimitées » de
`templates/payments/premium_marketplace.html` concerne un autre produit et ne
promet pas de messages, d’articles Business ou d’accès à tout l’écosystème.

Les pages `templates/about_us.html` et `templates/base.html` indiquent que la
candidature Meta est en cours d’examen / soumise à revue. Elles ne revendiquent
pas une approbation acquise. Le statut doit rester ainsi tant que Meta ne l’a pas
confirmé.

## Limites des packs affichées

| Limite de référence | `/tarifs/` | `/business/plans/` |
|---|---|---|
| Présence : 20 articles, 2 photos supplémentaires/article, 1 WABA/fiche, CRM et réponses texte 24 h, 5 crédits IA | Crédits IA affichés ; le plafond d’articles/photos, l’unité WABA, CRM et fenêtre 24 h ne sont pas tous explicités dans la carte. | Description dynamique mentionne CRM et réponses 24 h ; template affiche crédits IA, durée/boost. Plafond d’articles/photos et WABA non explicités dans la carte. |
| Croissance : 50 articles, 4 photos, 1 WABA/fiche, synchronisation catalogue Meta, relances avec modèle approuvé et consentement, 20 crédits IA, 7 jours boost | 20 crédits IA et 7 jours de boost visibles ; prix Business erroné ; sync Meta, limites du catalogue, WABA/fiche, consentement et modèle approuvé non explicités. | Crédits et boost dynamiques ; description du seed mentionne sync et relances à consentement ; limites catalogue, WABA et conditions d’activation ne sont pas rendues séparément. |
| Premium : sans plafond catalogue déclaré, 7 photos/article, 50 crédits IA, 15 jours boost et fonctions Business | 50 crédits IA et 15 jours de boost sont visibles ; aucun plafond catalogue ni 7 photos. Des libellés marketing (« Dominance totale ») ne sont pas une limite mesurable. | Crédits et boost affichés dynamiquement ; pas de limite catalogue/photos, WABA ou note conditionnelle WhatsApp explicitée. |
| Relances seulement individuelles, modèles Meta approuvés + consentement explicite ; pas de masse | Note absente sous la grille. | Description du seed mentionne les relances individuelles et consenties, mais la note « pas de messages de masse » et les conditions Meta/activation ne sont pas affichées sous la grille. |
| Frais Meta séparés, dépendance aux droits/configuration/approbation et absence de garantie d’approbation/résultat | Note absente sous les offres. | Note complète absente sous les offres. |

Les limites de catalogue se rapportent exclusivement au modèle `BusinessCatalogItem`.
Elles ne justifient pas de promettre une boutique `boutique.Produit` illimitée ou
isolée par entreprise. Le plafond technique de dix relances dues/minute du worker
est un paramètre de traitement, pas un quota contractuel client.

## Pages conformité : résultat dépôt

| Page | État du chemin/contenu local | Vérification |
|---|---|---|
| `/services/contact/` | **OK** | Template affiche siège Bepanda, Douala, BP 4241, Littoral, Cameroun ; bureau Bafoussam, Région de l’Ouest ; Business ID `1837509733943082` ; App ID `1841260056892991` ; WhatsApp `+237 680 62 50 82` ; `e.shelleltd@gmail.com`. Le site affiché dans le footer est `https://e-shelle.com`. |
| `/privacy-policy` | **OK au niveau route/template** | Route directe et template présents ; explique l’usage des données WhatsApp, le VPS InterServer communiqué et la non-revente. Vérifier que les déclarations correspondent aux pratiques réelles. |
| `/terms` | **OK au niveau route/template** | Route directe et template présents ; décrit le service et l’adresse Bepanda, Douala, BP 4241. |
| `/about` | **OK au niveau route/template** | Route directe et template présents ; fondateur et bureaux décrits ; statut Meta explicitement conditionné à l’examen/approbation. |
| `/business/plans/` | **OK au niveau route ; contenu à améliorer** | Route publique des ProviderPlan présente ; limite/prérequis WhatsApp non complets dans les cartes et formulation paiement Mobile Money ambiguë. |
| `/services/whatsapp-business/` | **KO — absent** | Aucun template correspondant ni route déclarée sous `services/urls.py`. |

Les routes légales sont des `TemplateView` sans décorateur d’authentification dans
le chemin inspecté. Cela indique qu’elles ne sont pas protégées par login dans
le code ; une vérification HTTP en production reste nécessaire.

## Remplacements recommandés

1. Dans `templates/tarifs.html`, remplacer le prix Business affiché **et le montant
   du texte prérempli WhatsApp** par `15 000 FCFA`.
2. Ajouter aux cartes commerciales les limites de catalogue, photos, une connexion
   WABA par fiche et les crédits/boost correspondant au plan, sans appeler le
   catalogue Business une boutique.
3. Afficher sous les plans cette note :

   > Les abonnements ne comprennent pas nécessairement les frais facturés par
   > Meta pour WhatsApp Business Platform. La connexion et la synchronisation
   > dépendent de la configuration, des droits et de l’approbation Meta. Les
   > relances sont individuelles, nécessitent un modèle approuvé et le consentement
   > explicite du contact ; les messages de masse ne sont pas inclus. E-Shelle ne
   > garantit ni l’approbation Meta ni un résultat commercial particulier.
4. Sur `business/templates/business/provider_plans.html`, remplacer la phrase
   générique de paiement par la formulation de validation manuelle donnée plus haut ;
   ajouter les limites exactes et la note de frais Meta/consentement.
5. Présenter Empire et Écosystème comme **sur devis, activation manuelle** et
   énumérer les modules inclus dans le devis. Ne pas afficher ces montants comme
   ProviderPlan automatisés.
6. La route dédiée `/services/whatsapp-business/` n’existe pas. Elle doit être
   créée et testée avant de communiquer cette URL à Meta ; ce rapport n’ajoute pas
   de route ni de template.

Aucun template n’a été modifié pendant cette vérification : le texte interdit exact
n’a pas été trouvé et l’action réalisée se limite au présent rapport. Le prix
périmé et les limites manquantes sont documentés pour correction approuvée ensuite.

## Trois commandes Git de contrôle

À utiliser après corrections autorisées ou pour examiner le worktree :

```bash
git diff --check
git diff --stat
git diff -- templates/tarifs.html business/templates/business/provider_plans.html templates/base.html templates/services/contact.html
```
