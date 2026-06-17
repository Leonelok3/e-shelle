# Guide Njangi Digital - Utilisation, vision et investisseurs

Version du 2 juin 2026  
Module E-Shelle analyse depuis le code Django `njangi`

---

## 1. Resume executif

Njangi Digital est le module E-Shelle dedie a la gestion des tontines, reunions et fonds communs. Il transforme une pratique communautaire souvent tenue dans des cahiers, groupes WhatsApp et notes individuelles en une application web structuree : groupes, membres, seances, cotisations, mains, depots, prets, remboursements, interets, audit et exports PDF.

La proposition de valeur est simple : donner aux associations, familles, reunions d'anciens eleves, groupes professionnels et diasporas un outil qui rend l'argent collectif plus lisible, plus traçable et plus equitable.

### Promesse produit

- Creer ou rejoindre une tontine avec un code d'invitation.
- Organiser les seances selon une frequence hebdomadaire, bimensuelle ou mensuelle.
- Suivre les cotisations, retards, penalites et mains versees.
- Gerer un fond commun qui finance des prets aux membres.
- Calculer les interets de facon proportionnelle selon les depots actifs.
- Produire des releves PDF membre et fond commun.
- Garder un journal d'audit des actions importantes.

---

## 2. Public cible

Njangi Digital s'adresse aux groupes qui manipulent une caisse collective et ont besoin de confiance operationnelle.

### Utilisateurs principaux

- President, tresorier et secretaire de reunion.
- Membres d'une tontine locale ou diasporique.
- Associations et mutuelles communautaires.
- Groupes de solidarite professionnelle.
- Familles qui organisent une epargne tournante.
- Petites caisses de pret communautaire.

### Besoins couverts

- Eviter les conflits de chiffres.
- Retrouver rapidement qui a paye, qui doit payer et qui a deja reçu.
- Rendre visible la sante du fond commun.
- Encadrer les prets et les remboursements.
- Donner a chaque membre un espace personnel.
- Presenter aux partenaires un systeme financier numerique coherent.

---

## 3. Parcours utilisateur

### 3.1 Creation du groupe

Le responsable cree le groupe depuis `/njangi/groupe/creer/`. Il definit le nom, la frequence, la cotisation par seance, le nombre maximum de membres, la date de depart, les taux du fond commun, les penalites et les regles de securite.

Le systeme genere automatiquement :

- un `slug` public du groupe ;
- un code d'invitation unique de 8 caracteres ;
- une adhesion du createur comme membre du bureau.

### 3.2 Invitation et adhesion

Les membres rejoignent le groupe depuis `/njangi/rejoindre/` avec le code d'invitation. Le plan gratuit limite le groupe a 5 membres, tandis que les plans payants retirent cette contrainte selon la configuration produit.

### 3.3 Espace membre

Chaque membre dispose d'un espace personnel :

- `/njangi/mon-espace/` : synthese des groupes et obligations.
- `/njangi/mon-espace/cotisations/` : historique des cotisations.
- `/njangi/mon-espace/prets/` : demandes et remboursements de prets.
- `/njangi/mon-espace/depots/` : depots dans le fond commun.
- `/njangi/mon-espace/portefeuille/` : solde, interets et evolution mensuelle.
- `/njangi/mon-espace/notifications/` : alertes et rappels.

### 3.4 Espace bureau

Le bureau gere le groupe depuis `/njangi/bureau/<slug>/`. Les roles autorises sont president, tresorier et secretaire.

Fonctions disponibles :

- tableau de bord du groupe ;
- gestion des membres ;
- creation et cloture des seances ;
- suivi des prets ;
- gestion du fond commun ;
- calcul des interets mensuels ;
- reconciliation financiere ;
- journal d'audit.

---

## 4. Fonctionnalites principales

### 4.1 Groupes et membres

Le modele `Group` porte l'identite et les regles de la tontine : frequence, montant de cotisation, nombre maximal de membres, taux de pret, taux de depot, penalite journaliere, reserve du fond et fonds de base obligatoire.

Le modele `Membership` relie un utilisateur au groupe. Il conserve le role, l'ordre de main, les totaux cotises, les montants reçus, les penalites et le score de fiabilite.

### 4.2 Seances et cotisations

Une `Session` represente une reunion de tontine. Elle passe par les statuts planifiee, en cours, cloturee ou annulee. Les cotisations sont creees pour chaque membre et peuvent etre payees via MTN Mobile Money, Orange Money, especes ou virement.

Chaque `Contribution` suit le montant du, le montant paye, le statut, la methode de paiement, la reference de transaction et les penalites de retard.

### 4.3 Main ou bouffe

La main correspond au montant distribue au beneficiaire d'une seance. Le service `DistributionCalculator` calcule un aperçu avant versement :

- montant brut attendu ;
- deficit eventuel du fonds de base obligatoire ;
- solde d'un pret actif ;
- penalites impayees ;
- cotisations en retard ;
- montant net pouvant etre verse.

Cette logique reduit les distributions injustes et donne au bureau une vue claire avant validation.

### 4.4 Fond commun

Le fond commun est alimente par les depots volontaires, penalites, remboursements et interets de prets. Il finance les prets accordes aux membres.

Les mouvements sont enregistres dans `FundTransaction` avec un signe automatique :

- entrees : depot, remboursement, interets, penalites, ajustements ;
- sorties : retrait, pret decaisse, interets verses, main payee, depense.

### 4.5 Prets et remboursements

Le modele `Loan` couvre tout le cycle :

- demande ;
- approbation ;
- refus ;
- decaissement ;
- remboursement ;
- defaut ;
- cloture.

Les interets sont calcules simplement sur le capital approuve, selon le taux mensuel du groupe et la duree du pret. Les remboursements enregistrent la part interets, la part capital et le solde restant.

### 4.6 Interets proportionnels

La logique differentiatrice de Njangi Digital est le calcul mensuel des interets proportionnels.

Formule :

```text
pool_total = somme des depots actifs du mois
interets_generes = somme(montant_pret * taux_pret / 100)
interet_membre = depot_membre / pool_total * interets_generes
```

Un membre gagne donc selon sa contribution reelle au pool qui finance les prets actifs. Si aucun pret n'est actif, le mois ne genere pas d'interets a redistribuer.

Les resultats sont stockes dans :

- `MonthlyGroupInterest` pour le snapshot mensuel du groupe ;
- `MemberMonthlyStatement` pour le releve individuel de chaque deposant.

### 4.7 Score de fiabilite

Le score de fiabilite commence a 100 et evolue selon le comportement du membre.

- Cotisation payee a temps : +2 points.
- Cotisation en retard ou partielle : -5 points.
- Cotisation absente apres la date de seance : -10 points.
- Pret rembourse : +5 points.
- Pret actif en retard : -10 points.
- Pret en defaut : -20 points.

Ce score aide le bureau a prendre des decisions de pret plus rationnelles.

### 4.8 Reconciliation et audit

Le service `FundReconciliationService` compare les transactions du fond avec les prets actifs, depots actifs, remboursements et interets calcules. Il signale les ecarts de prets ou de depots.

Le modele `AuditLog` garde la trace des actions majeures : creation et cloture de seance, paiement, demande de pret, approbation, decaissement, depot, retrait, changement de plan, calcul d'interets et ajustement de fond.

---

## 5. Exports PDF inclus dans l'application

Le module contient deja deux exports PDF operationnels cote application :

- releve membre : `/njangi/mon-espace/releve-pdf/` ;
- releve du fond commun : `/njangi/bureau/<slug>/fond/pdf/`.

Ces exports sont utiles pour imprimer une situation individuelle, presenter les comptes en reunion ou archiver la periode.

---

## 6. Administration et automatisation

### Administration Django

L'admin expose les objets principaux :

- groupes et membres ;
- seances et cotisations ;
- depots et transactions du fond ;
- prets et remboursements ;
- notifications et documents ;
- interets mensuels ;
- demandes d'abonnement ;
- journal d'audit.

### Commandes de gestion

Le module propose des commandes Django :

```bash
python manage.py seed_njangi
python manage.py seed_njangi_demo
python manage.py calculate_monthly_interests
```

La commande de calcul des interets permet le mois courant, un groupe specifique, un mois donne, le recalcul historique, le mode simulation et le `dry-run`.

### Taches planifiees

Le projet reference des taches Celery pour :

- calculer les interets mensuels ;
- appliquer les penalites quotidiennes ;
- verifier les prets en defaut ;
- mettre a jour les scores de fiabilite.

---

## 7. Modele economique

Le code contient quatre plans :

| Plan | Prix indicatif | Limite membres |
| --- | ---: | --- |
| Gratuit | 0 FCFA | 5 membres |
| Standard | 3 000 FCFA | illimite |
| Pro | 7 000 FCFA | illimite |
| Association | 15 000 FCFA | illimite |

Le plan gratuit sert d'entree pour tester le produit. Les plans payants monetisent les groupes actifs qui ont besoin d'une gestion complete et durable.

---

## 8. Opportunite investisseurs

Njangi Digital occupe un espace a fort potentiel : les finances communautaires africaines. Les tontines sont deja largement adoptees, mais la gestion reste souvent manuelle. L'application ne cherche pas a changer la culture de la tontine ; elle apporte une couche de confiance, d'historique et d'automatisation.

### Atouts du produit

- Usage ancre dans une pratique existante.
- Adoption facilitee par le mobile web.
- Donnees financieres recurrentes et utiles.
- Extension naturelle vers paiements, credit scoring, assurance, epargne et marketplace.
- Integration dans la suite E-Shelle, avec chat IA, business dashboard et marketing.

### Effets reseau

Chaque groupe invite plusieurs membres. Un membre satisfait peut creer son propre groupe, recommander l'outil a une autre association ou utiliser d'autres services E-Shelle.

---

## 9. Risques et points de vigilance

### Risques produit

- Besoin d'une UX tres simple pour les tresoriers non techniques.
- Necessite de clarifier la responsabilite legale sur les fonds manipules.
- Importance des sauvegardes, exports et audit pour conserver la confiance.
- Sensibilite des donnees financieres personnelles.

### Recommandations

- Ajouter une page de regles de groupe lisible avant adhesion.
- Renforcer les permissions fines entre president, tresorier et secretaire.
- Ajouter des notifications WhatsApp/SMS pour retards, seances et remboursements.
- Connecter progressivement Mobile Money pour rapprocher paiement reel et preuve applicative.
- Ajouter des tableaux de bord de croissance et retention pour le pilotage commercial.

---

## 10. Conclusion

Njangi Digital est un module strategique pour E-Shelle : il combine une pratique sociale massive, une douleur operationnelle reelle et une logique financiere mesurable. Son architecture couvre deja les bases essentielles d'une tontine moderne : membres, bureau, seances, cotisations, prets, fonds commun, interets, PDF et audit.

La prochaine valeur a creer se situe dans l'adoption terrain : simplification de l'interface, automatisation des rappels, integration des paiements et mise en avant de cas d'usage concrets pour associations, familles et diaspora.
