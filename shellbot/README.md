# ShellBot - Assistant WhatsApp IA pour PME

ShellBot est un produit standalone inspire des briques WhatsApp et IA d'E-Shelle.

Positionnement:

- 0$ le premier mois;
- puis 5$/mois;
- cible: PME canadiennes, Quebec et Ontario francophone en priorite;
- stack: FastAPI, WhatsApp Business Cloud API, SQLite ou PostgreSQL, Docker.

## Fonctionnalites

- Reponses automatiques intelligentes avec FAQ dynamique.
- Base de connaissance par tenant via JSON.
- Collecte de prospects: nom, email, telephone, besoin, langue.
- Generation de devis texte structure.
- Export CSV des prospects et devis.
- Rendez-vous via lien Calendly ou creneaux simples.
- Detection francais / anglais.
- Dashboard web leger.
- Multi-tenant par numero WhatsApp Business.
- Onboarding conversationnel par WhatsApp.
- Fallback humain avec notification email.

## Demarrage local

```bash
cd shellbot
copy .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8088
```

Dashboard:

```text
http://127.0.0.1:8088/
```

Webhook Meta:

```text
GET/POST http://127.0.0.1:8088/webhooks/meta
```

## Docker

```bash
cd shellbot
docker compose up --build
```

## Configuration PME

Chaque PME est un tenant. Les exemples sont dans:

```text
config/tenants.example.json
```

Le champ important pour router les messages entrants est:

```json
"phone_number_id": "META_PHONE_NUMBER_ID"
```

## Variables Meta

```env
META_VERIFY_TOKEN=un_secret_webhook
META_ACCESS_TOKEN=EAAB...
META_API_VERSION=v20.0
SHELLBOT_DRY_RUN=true
```

En `SHELLBOT_DRY_RUN=true`, ShellBot log les messages sortants sans appeler Meta.

## Notes de conformite

ShellBot ne doit traiter que des contacts ayant initie la conversation ou ayant donne un consentement valide. Les campagnes de masse et le scraping de groupes WhatsApp ne sont pas inclus.

