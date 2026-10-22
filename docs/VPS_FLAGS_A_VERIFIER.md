# Variables WhatsApp à vérifier sur `vps3581805`

Cette checklist est à exécuter manuellement par une personne autorisée sur le VPS.
L’assistant n’a pas d’accès SSH et ne doit pas tenter d’en obtenir. Ne pas copier
de valeur de secret dans un ticket, un terminal partagé ou un rapport.

| Variable | Vérification attendue |
|---|---|
| `WHATSAPP_COMMERCE_ENABLED` | `true` uniquement lorsque l’envoi Business tenant-scoped a été testé et activé. |
| `WHATSAPP_BUSINESS_AUTOMATIONS_ENABLED` | Vérifier la décision d’activation séparément ; ce flag concerne aussi les relances planifiées. |
| `WHATSAPP_DRY_RUN` | Doit être `false` pour un envoi réel. Confirmer le mode avant toute campagne. |
| `WHATSAPP_TECH_PROVIDER_APP_ID` | Vérifier que l’App ID correspond à l’application Meta Tech Provider approuvée. Ne pas publier d’identifiant erroné. |
| `WHATSAPP_API_URL` | Vérifier la version Graph API et le `phone_number_id` prévu pour l’envoi global historique. Ne jamais partager le jeton associé. |

Consigner pour chaque variable : valeur booléenne ou présence/absence, date,
personne ayant vérifié et résultat d’un test contrôlé. Ne pas inclure de jeton,
secret d’application, contenu `.env` ou identifiant d’accès.

`GET /api/tech-provider/status` fournit un aperçu non secret des flags et des
présences de configuration dans l’application locale ; il ne prouve pas qu’un
service, worker, webhook ou compte Meta fonctionne en production. L’endpoint est
réservé au personnel authentifié.
