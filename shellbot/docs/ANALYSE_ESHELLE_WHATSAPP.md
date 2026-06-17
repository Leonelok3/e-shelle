# Analyse E-Shelle - agents WhatsApp et patterns reutilisables

## Agents WhatsApp identifies

### `whatsapp_agent`

Agent Django de campagnes WhatsApp.

Fonctions:

- carnet de contacts WhatsApp autorises;
- import manuel/API de contacts;
- creation de campagnes;
- personnalisation de messages;
- generation IA de messages courts via Anthropic;
- envoi Cloud API Meta;
- mode `WHATSAPP_DRY_RUN`;
- suivi `envoye`, `livre`, `lu`, `echec`;
- webhook Meta pour verification et statuts;
- export CSV des campagnes;
- synchronisation vers l'agent commercial.

Patterns reutilisables:

- `ContactWhatsApp`, `Campagne`, `MessageEnvoi`;
- normalisation numero local et format Meta;
- dry-run avant production;
- consentement obligatoire;
- webhook GET/POST Meta;
- separation service metier / vues / taches Celery.

### `whatsapp_extractor`

Outil Node local pour preparer et importer des contacts opt-in.

Fonctions:

- lire CSV/XLS/XLSX;
- reconnaitre colonnes `nom`, `numero`, `ville`, `groupe`, `note`;
- dedupliquer;
- exiger `WHATSAPP_IMPORT_CONSENT=oui`;
- importer via `POST /whatsapp/api/import-contact/`.

Patterns reutilisables:

- pipeline propre CSV -> normalisation -> API;
- barriere de consentement;
- format de donnees simple pour PME.

### `phone_ocr_agent`

Agent OCR local pour captures de numeros.

Fonctions:

- upload PNG/JPG;
- OCR local `pytesseract` + Pillow;
- extraction regex de numeros;
- normalisation WhatsApp;
- export CSV.

Patterns reutilisables:

- OCR local sans envoyer l'image a une API externe;
- sortie structurée utilisable par un import contacts;
- affichage texte brut + numeros detectes.

### `commercial_agent`

Agent commercial IA pour convertir les contacts en prospects.

Fonctions:

- scoring prospect;
- plan recommande;
- montant potentiel;
- generation de messages commerciaux;
- relances;
- creation de campagnes depuis prospects dus;
- synchronisation depuis contacts WhatsApp.

Patterns reutilisables:

- score prospect;
- statut pipeline;
- relance programmee;
- fallback si API IA absente.

### Modules metier avec liens WhatsApp

Modules comme `pressing`, `resto`, `sante`, `transport_core` generent des liens `wa.me` avec message pre-rempli pour commande, rendez-vous ou contact.

Pattern reutilisable:

- CTA simple, direct, sans dependance API;
- utile pour fallback humain et notification au commerçant.

## APIs et bibliotheques observees

- Meta WhatsApp Business Cloud API via `requests`.
- Anthropic Claude pour messages marketing.
- OpenAI dans d'autres agents E-Shelle.
- Twilio dans `tchaslucpay` pour SMS, pas WhatsApp.
- Celery pour envois asynchrones.
- Django REST Framework token auth pour import contacts.
- pytesseract/Pillow pour OCR local.
- Node `xlsx`, `csv-parse`, `axios` pour import CSV/Excel.

## Fonctionnalites IA deja implementees dans E-Shelle

- Chat/agent central E-Shelle.
- Generation marketing AdGen.
- Agent commercial IA.
- Agent WhatsApp generation de campagnes.
- Agent SEO audit, schema, CTA, pages locales.
- OCR local telephone.
- Audio Studio IA prototype.
- Coach IA preparation tests/langues.
- Love coach rencontres.
- Agent demandes non satisfaites et opportunites commerciales.
- Agent LEBELAGE/Shopify pour extraction/export/import brouillon.

## Ce qui est reutilisable pour ShellBot standalone

- Architecture `Contact/Campaign/Message` transformee en `Tenant/Conversation/Message/Lead/Quote`.
- Webhook Meta et dry-run.
- Consentement et import structure.
- Normalisation telephone.
- FAQ JSON.
- Generation IA avec fallback sans cle API.
- Export CSV.
- Fallback humain email.
- Dashboard leger.

## Difference produit

E-Shelle est une plateforme multi-modules. ShellBot doit rester un produit simple:

```text
Un assistant WhatsApp IA pour une PME, capable de repondre, qualifier, faire un devis, prendre rendez-vous et alerter un humain.
```

