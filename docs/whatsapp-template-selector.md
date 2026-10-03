# Selection des modeles Meta

La creation et le detail d'une campagne proposent la liste des modeles APPROVED
du compte possedant le numero configure. Le choix, la langue, les variables et
l'apercu sont enregistres avec la campagne. Le test et les workers utilisent ces
memes informations. `{{prenom}}` dans une variable utilise le prenom du destinataire.
La duplication conserve cette configuration. Les messages historiques ne sont pas modifies.

## Configuration serveur

Configurer dans l'environnement, sans committer de token :

```
WHATSAPP_WABA_ID=<ID du compte WhatsApp Business qui possede le numero>
WHATSAPP_PHONE_ID=<Phone Number ID du meme compte>
WHATSAPP_TOKEN=<token autorise pour ce compte>
```

Le token doit pouvoir lire les comptes, numeros et modeles via
`whatsapp_business_management` et envoyer via `whatsapp_business_messaging`.
Le Business ID du portefeuille n'est pas le WABA ID. Si le WABA ID est absent,
`WHATSAPP_BUSINESS_ID` permet de rechercher le compte parmi les comptes propres
et clients accessibles. L'application verifie l'appartenance du Phone Number ID.
Un numero de test et son compte ne donnent pas acces aux modeles d'un autre compte.
Le catalogue utilise la version de `WHATSAPP_API_URL` et un cache de deux minutes.
Le test et le lancement revalident le modele sans cache.

Les modeles avec variables numerotees du corps, en-tete texte fixe et boutons
URL fixes / telephone sont pris en charge. Les medias, boutons dynamiques,
quick replies et variables nommees sont affiches comme non pris en charge.
Un modele invalide bloque l'envoi avec une explication ; aucun remplacement
automatique par un message texte n'est effectue pour un modele selectionne.

## Installation et verification

Apres installation du code sur le serveur :

```
python manage.py migrate whatsapp_agent
python manage.py collectstatic --noinput
```

Redemarrer Django et les workers Celery selon la procedure de deploiement du projet.
Conserver les reglages de simulation existants pour les essais sans envoi reel.
Ne pas activer le mode reel automatiquement pendant le deploiement.

Dans le detail d'une campagne encore non lancee : choisir le modele, renseigner
ses variables, cliquer sur « Enregistrer le modele pour la campagne », puis
utiliser le test. L'apercu affiche le corps du modele personnalise. Verifier la
livraison dans le suivi des tests avant de lancer la campagne. L'acceptation API
n'est pas une confirmation de livraison.

Verification automatisee sans appels Meta ni messages reels :

```
python manage.py test whatsapp_agent --settings=whatsapp_agent.test_settings --noinput
```
