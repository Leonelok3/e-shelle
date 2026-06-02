# E-Shelle - Import Contacts WhatsApp autorises

Cet outil local sert a importer dans Django des contacts WhatsApp que tu as le droit de contacter: clients, prospects opt-in, fichiers commerciaux propres, formulaires, anciennes commandes, etc.

Il ne contourne pas WhatsApp et ne sert pas a aspirer les membres d'un groupe sans autorisation.

## Installation

```bash
cd whatsapp_extractor
npm install
copy .env.example .env
```

Dans `.env`, configure:

```env
ESHELLE_API_BASE_URL=http://127.0.0.1:8025
ESHELLE_API_TOKEN=ton_token_django
WHATSAPP_IMPORT_CONSENT=oui
```

`WHATSAPP_IMPORT_CONSENT=oui` veut dire que tu confirmes que les contacts ont accepte d'etre contactes.

## Format du fichier

CSV ou Excel avec au moins une colonne numero. Colonnes reconnues:

- `nom`, `name`, `prenom`, `client`
- `numero`, `phone`, `telephone`, `whatsapp`, `tel`
- `ville`, `city`
- `groupe`, `group`, `source_groupe`
- `note`, `commentaire`, `comment`

## Utilisation

Preparer un CSV propre:

```bash
npm run prepare -- contacts-source.xlsx
```

Importer vers E-Shelle:

```bash
npm run import -- exports/contacts-whatsapp-xxxx.csv
```

Menu interactif:

```bash
npm start
```

## Creer un token Django

En local:

```bash
python manage.py drf_create_token admin_eshelle
```

Ou avec ton venv:

```bash
.\.venv\Scripts\python.exe manage.py drf_create_token admin_eshelle
```

L'API appelee est:

```text
POST /whatsapp/api/import-contact/
Authorization: Token <token>
```
