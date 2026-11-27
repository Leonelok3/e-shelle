# Pilote de l’import WhatsApp

Utiliser deux fiches Business distinctes et deux prestataires volontaires. Associer le numéro WhatsApp habituel de chaque testeur à sa propre fiche. Préparer un numéro Meta de test dédié à l’import, raccordé au webhook signé E-Shelle, et utiliser des produits fictifs.

## Trois offres par prestataire

| Scénario | Message à transférer | Résultat attendu |
| --- | --- | --- |
| Photo avec légende | Photo légendée « Lampe de test, 9 000 F CFA, réf. PILOTE-01 » | Avec la publication directe activée, une lampe apparaît sur la bonne fiche, avec la photo, le prix et le lien envoyé sur WhatsApp. |
| Photo séparée | Texte « Ventilateur de test, 18 000 F CFA, réf. PILOTE-02 », puis photo sans légende | Depuis la photo à valider, choisir **Rattacher à un produit**, sélectionner le ventilateur et confirmer l’aperçu. Vérifier que le prix de 18 000 F CFA est conservé et qu’un seul ventilateur existe. Le premier prestataire peut tester un article déjà publié. Le second désactive la publication directe pour tester un brouillon. |
| Modification de prix | « Lampe de test, 10 000 F CFA, réf. PILOTE-01 » | Le produit reste à 9 000 F CFA jusqu’à la validation du propriétaire. Après confirmation, la même lampe passe à 10 000 F CFA. |

## Relevé

| Prestataire | Scénario | Bonne fiche | Ressaisie du produit ou du prix | Correction nécessaire | Lien WhatsApp reçu | Remarque |
| --- | --- | --- | --- | --- | --- | --- |
| A | Photo légendée | | | | | |
| A | Photo séparée → article publié | | | | | |
| A | Modification de prix | | | | | |
| B | Photo légendée | | | | | |
| B | Photo séparée → brouillon | | | | | |
| B | Modification de prix | | | | | |

Compter séparément les offres arrivées sur la bonne fiche sans ressaisie et celles qui ont demandé une correction. Une validation attendue, comme le choix d’un article ou la confirmation d’un nouveau prix, ne compte pas comme une correction.

## Du lien partagé au résultat

Tester avec un restaurant et une agence disposant chacun d’un numéro Business connecté, du Vendeur WhatsApp actif et d’une fiche publique. Depuis **Résultats par offre**, noter les compteurs de départ et partager les liens de deux offres de test dans un chat privé. Utiliser un second compte WhatsApp pour jouer le client.

| Profil | Parcours | Vérification |
| --- | --- | --- |
| Restaurant | Ouvrir le lien du plat et appuyer sur le bouton WhatsApp. Envoyer le message prérempli, écrire `COMMANDER`, répondre `OUI`, puis suivre le paiement. | Le clic précède le message reçu. Le paiement en attente ne compte pas. Un paiement vérifié en production ou validé depuis le parcours manuel existant ajoute une commande payée. Un paiement CamPay sandbox ne change pas le compteur des ventes réelles. |
| Agence | Ouvrir le lien d’un bien disponible puis cliquer sur **Demander une visite sur WhatsApp**. Envoyer le message prérempli et renvoyer un créneau proposé. | Le bon bien est reconnu. La proposition ne suffit pas pour le compteur. La confirmation l’incrémente sur ce bien. Un report conserve un résultat et une annulation le retire. |

Rouvrir le lien de la même offre depuis le même compte, puis renvoyer le message. Vérifier que le clic supplémentaire est visible et que ce contact compte toujours pour une seule conversation sur cette offre. Depuis un autre compte, envoyer une demande WhatsApp sans passer par le lien et vérifier qu’aucun résultat n’est attribué par défaut. Pour tester un salon, associer l’agenda dans l’activation WhatsApp et donner le même nom à la prestation active de cet agenda et à l’article de type Service sur la fiche.

## Reprise par l’équipe

Depuis **WhatsApp Business → À reprendre**, partir d’une commande confirmée dont le paiement est encore en attente. Vérifier le montant, l’état du paiement et le lien vers la conversation. Après vérification du paiement réel, actualiser la rubrique et constater que le dossier a disparu.

Pour l’agence, demander une visite et envoyer « Aucun créneau ne me convient ». Vérifier que le dossier désigne le bon bien. Choisir ensuite un créneau et confirmer la visite dans le même échange. Vérifier que le dossier se ferme et qu’un dossier pour un autre bien reste ouvert.

Poser une question qui nécessite une réponse de l’équipe, puis ouvrir la conversation depuis le dossier. Répondre et cliquer sur **Marquer comme traité**. Relever le temps nécessaire à la reprise et toute information manquante dans le dossier. La reprise utilise les règles d’envoi existantes dans WhatsApp Business.

## Automatisations après confirmation

Depuis **WhatsApp Business → Automatisations**, choisir un délai et le nom exact d’un modèle utilitaire approuvé pour le WABA de la fiche. Activer les relances sur la connexion et sur le serveur. Utiliser un contact de test dont le consentement est enregistré.

| Automatisation | Exemple de texte du modèle | Boutons de réponse rapide dans l’ordre |
| --- | --- | --- |
| Rappel de rendez-vous | « Ton rendez-vous pour {{1}} est prévu le {{2}}. Peux-tu confirmer ta présence ? » | Confirmer ma présence, Reporter |
| Relance de paiement CamPay | « Le paiement de ta commande {{1}} est en attente. Voici le lien pour régler ta commande {{2}}. » | Aucun |
| Suivi après un rendez-vous | « Suite à ton rendez-vous pour {{1}} chez {{2}}, souhaites-tu poursuivre l’échange ? » | Répondre |
| Suivi après une livraison | « Ta commande {{1}} a été livrée par {{2}}. Comment s’est passée la livraison ? » | Répondre |

Les deux variables sont positionnelles. Les modèles sont soumis puis approuvés dans le gestionnaire Meta avant leur utilisation par E‑Shelle. [Documentation Meta sur les modèles interactifs](https://developers.facebook.com/docs/whatsapp/api/messages/message-templates/interactive-message-templates/)

- Reporter une visite depuis le rappel. Choisir une ligne `REPORTER` de la réponse, vérifier le nouveau créneau dans l’agenda et comparer avec l’historique. Rejouer l’ancien bouton pour vérifier que l’ancien créneau reste obsolète. Faire un second test avec un agenda plein et vérifier l’apparition du dossier dans **À reprendre**.
- Réconcilier une commande CamPay après planification et avant l’envoi. Vérifier que la relance est annulée. Sur une commande d’essai encore en attente, vérifier que le lien ouvre le checkout de cette commande.
- Marquer une visite comme réalisée et une commande payée comme livrée. Après le délai, vérifier l’envoi du bon modèle. Utiliser le bouton **Répondre** ou répondre au message WhatsApp cité, puis vérifier le dossier dans **À reprendre**.
- Mettre une règle en pause ou retirer le consentement avant l’envoi et vérifier l’absence de nouvel envoi. Consulter le statut et les réponses dans **Historique des automatisations**.

## Validation depuis Mes agents

Avant le partage, ouvrir **Mes agents** avec chaque entreprise, relever les étapes manquantes et chronométrer la connexion, la première offre et le premier test réussi. Au terme du pilote, relever les clics, les contacts référencés, les commandes payées, les rendez-vous confirmés et les interventions de l’équipe. Le gérant peut s’envoyer le récapitulatif depuis cette page.

- Pour une boutique, tester sur un article au stock suivi. Confirmer deux commandes susceptibles d’épuiser le stock et vérifier que la seconde est refusée si le disponible est insuffisant. Annuler une commande qui n’a pas engagé de paiement et vérifier la restitution unique. Pour une commande payée, renseigner la préparation, l’expédition ou la livraison, puis tester `SUIVI`, `REÇU` et `SAV` avec la référence. Après livraison, vérifier le déclenchement du suivi configuré.
- Pour la notification d’expédition, utiliser par exemple « La commande {{1}} est expédiée. Information de livraison {{2}} », sans bouton. Vérifier que le passage à **Expédiée** planifie l’envoi et que le passage à **Livrée** le rend obsolète si le message n’est pas encore parti.
- Depuis **Devis et relances**, préparer un devis, le valider et l’envoyer à un contact de test. Utiliser la commande d’acceptation depuis la même conversation et vérifier la remontée dans **À reprendre**. Un autre contact ne peut pas accepter ce devis.
- Pour la **liste d’attente**, configurer le modèle « Une place pour {{1}} est disponible {{2}} », avec deux variables et aucun bouton. Depuis le WhatsApp de test, envoyer `LISTE D’ATTENTE`, puis ouvrir un créneau et vérifier que seul le prochain créneau est signalé. L’inscription à l’alerte ne réserve pas le créneau.
- Pour l’**alerte immobilier**, configurer le modèle « Un nouveau bien {{1}} correspond à ta recherche. Voir le bien {{2}} », avec deux variables et aucun bouton. Indiquer les critères puis envoyer `ALERTE BIENS`. Publier un bien correspondant sous la bonne agence et vérifier que le lien pointe vers cette annonce. Tester aussi `STOP ALERTES` avant un envoi planifié.

## Du premier résultat au renouvellement

Depuis **Ma Business Key → Portefeuille prestataires**, copier le lien d’invitation et suivre la création d’une fiche par le compte de test. Depuis **Bilan et renouvellement**, le gérant peut partager ses étapes d’accompagnement avec le partenaire de parrainage. Vérifier qu’un autre partenaire ne voit pas la fiche et que le retrait du partage la masque aussitôt.

Dans le bilan, comparer les commandes et rendez-vous aux résultats par offre, puis suivre le lien de renouvellement. Vérifier que le checkout indique la bonne fiche et la bonne formule. Sur des transactions simulées, rejouer la confirmation d’un même paiement et vérifier une seule prolongation et une seule commission. Une confirmation sandbox ne doit créer aucune commission réelle. Au pilote, relever le nombre de prestataires arrivés au premier résultat et le nombre qui renouvellent au prochain cycle.
