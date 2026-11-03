# Tarifs prestataires E-Shelle — grille de vente

**Grille approuvée le 3 novembre 2026.** Ce document remplace les anciennes
propositions de prix des fiches Business présentes dans les documents marketing.
Les prix sont affichés en FCFA, par fiche et pour 30 jours.

| Formule | Prix / 30 jours | Limites et valeur principale |
|---|---:|---|
| Gratuit | 0 FCFA | Fiche de base, lien de contact WhatsApp et jusqu'à 5 articles. Pas de CRM WhatsApp. |
| Présence — Pro | 5 000 FCFA | Jusqu'à 20 articles, 2 photos supplémentaires par article, 5 crédits IA, connexion WhatsApp et CRM avec réponses dans la fenêtre de service. |
| Croissance — Business | 15 000 FCFA | Jusqu'à 50 articles, 4 photos supplémentaires par article, 20 crédits IA, 7 jours de Boost E-Shelle et synchronisation au catalogue Meta associé. Relances individuelles seulement si la configuration est activée, avec modèle approuvé et consentement explicite. |
| Premium | 30 000 FCFA | Catalogue sans plafond déclaré dans le code, 7 photos supplémentaires par article, 50 crédits IA et 15 jours de Boost E-Shelle. |

## Positionnement vendu

**E-Shelle aide les entreprises locales à être trouvées, à vendre sur WhatsApp et
à suivre leurs clients.** Les outils de visibilité locale, SEO et préparation
des contenus pour les moteurs de recherche et assistants IA sont des outils
logiciels de la plateforme. Ils ne garantissent pas une position Google, une
citation par un LLM, un volume de prospects ou des ventes.

Un accompagnement humain de référencement, la gestion d'une fiche Google
Business Profile, la rédaction supplémentaire ou l'optimisation effectuée pour
le client ne sont pas inclus dans Premium : ils font l'objet d'un devis séparé.

## Conditions commerciales à afficher

- L'abonnement est par fiche Business, pour 30 jours.
- Les frais de conversations et de messagerie WhatsApp Platform sont à la charge
  du client et facturés séparément par Meta.
- Les réponses libres sont soumises à la fenêtre de service WhatsApp. Les
  relances hors fenêtre nécessitent les modèles applicables, le consentement
  explicite et l'activation technique. Les campagnes de masse ne sont pas
  incluses dans le CRM WhatsApp Business par fiche.
- L'approbation Meta, la livraison des messages, le classement Google et les
  résultats commerciaux ne sont pas garantis par l'abonnement.
- Les ventes multi-modules, sites sur mesure et services humains sont chiffrés
  séparément après définition du périmètre.

## État de publication

Les prix de référence sont inscrits dans la page publique et dans le seeder
`business/management/commands/seed_business_plans.py`. La page
`/business/plans/` lit les montants de la base `ProviderPlan`; la page
`/tarifs/` affiche les prix dans son gabarit. Le code local ne prouve pas que le
déploiement est effectué ni que le seeder a été exécuté sur la base de
production. Avant d'accepter un paiement, déployer les changements, synchroniser
les plans de production par la procédure de mise en production et vérifier les
montants rendus sur le site en ligne.
