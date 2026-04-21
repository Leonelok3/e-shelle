from django.db import migrations

DEFAULT_SUBJECT = "Recrutez des talents africains qualifiés — Immigration97"

DEFAULT_BODY_TEXT = """
{greeting}

Je me permets de vous contacter au nom de la plateforme Immigration97.com.

Nous accompagnons des centaines de candidats africains qualifiés dans leur projet
d'immigration professionnelle au {country_label}, notamment dans le secteur {sector_label}.

Nos candidats disposent de :
- CV optimisés pour le marché {country_label}
- Niveaux de langue certifiés (TEF, TCF, IELTS)
- Dossiers d'immigration complets

Visiter notre plateforme pour consulter les profils disponibles :
https://immigration97.com/profiles/

Si vous recrutez actuellement ou prévoyez de le faire, nous pouvons vous mettre
directement en relation avec des candidats correspondant à vos critères, gratuitement.

N'hésitez pas à créer votre compte recruteur (gratuit) sur :
https://immigration97.com/recruteur/

Cordialement,
L'équipe Immigration97
contact@immigration97.com | +237 693 649 944
""".strip()

DEFAULT_BODY_HTML = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,Helvetica,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f4f5;padding:30px 0">
  <tr>
    <td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.08)">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#050A18,#0f1f3d);padding:28px 40px;text-align:center">
            <p style="margin:0;font-size:22px;font-weight:800;color:#D4A843;letter-spacing:-0.5px">
              Immigration97
            </p>
            <p style="margin:6px 0 0;font-size:12px;color:rgba(255,255,255,0.60);text-transform:uppercase;letter-spacing:2px">
              Talents Africains Qualifiés
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 28px">
            <p style="font-size:16px;color:#111827;margin:0 0 20px">{greeting}</p>

            <p style="color:#374151;line-height:1.7;margin:0 0 16px">
              Je me permets de vous contacter au nom de la plateforme
              <strong style="color:#D4A843">Immigration97.com</strong>.
            </p>

            <p style="color:#374151;line-height:1.7;margin:0 0 20px">
              Nous accompagnons des centaines de candidats africains qualifiés
              dans leur projet d'immigration professionnelle au <strong>{country_label}</strong>,
              notamment dans le secteur <strong>{sector_label}</strong>.
            </p>

            <!-- Avantages -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;margin-bottom:24px">
              <tr>
                <td style="padding:20px 24px">
                  <p style="font-weight:700;color:#111827;margin:0 0 12px;font-size:14px">
                    Nos candidats disposent de :
                  </p>
                  <table cellpadding="0" cellspacing="0">
                    <tr>
                      <td style="padding:4px 0;color:#374151;font-size:14px">✅&nbsp; CV optimisés ATS pour le marché {country_label}</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 0;color:#374151;font-size:14px">✅&nbsp; Niveaux de langue certifiés (TEF, TCF, IELTS, DELF)</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 0;color:#374151;font-size:14px">✅&nbsp; Dossiers d'immigration complets et vérifiés</td>
                    </tr>
                    <tr>
                      <td style="padding:4px 0;color:#374151;font-size:14px">✅&nbsp; Candidats motivés et disponibles immédiatement</td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <!-- CTA principal -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px">
              <tr>
                <td align="center">
                  <a href="https://immigration97.com/profiles/"
                     style="display:inline-block;background:linear-gradient(135deg,#D4A843,#E8B84B);
                            color:#0a0f1e;font-weight:800;font-size:15px;text-decoration:none;
                            padding:14px 32px;border-radius:8px;letter-spacing:0.3px">
                    Consulter les profils disponibles →
                  </a>
                </td>
              </tr>
            </table>

            <p style="color:#374151;line-height:1.7;margin:0 0 20px">
              La mise en relation entre recruteurs et candidats est
              <strong>entièrement gratuite</strong> pour les entreprises.
              Créez votre compte recruteur en 2 minutes :
            </p>

            <!-- CTA secondaire -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:28px">
              <tr>
                <td align="center">
                  <a href="https://immigration97.com/recruteur/"
                     style="display:inline-block;background:#050A18;
                            color:#D4A843;font-weight:700;font-size:14px;text-decoration:none;
                            padding:11px 28px;border-radius:8px;border:2px solid #D4A843">
                    Créer mon compte recruteur (gratuit)
                  </a>
                </td>
              </tr>
            </table>

            <p style="color:#6b7280;font-size:13px;line-height:1.7;margin:0">
              Si vous n'êtes pas intéressé(e) par ce type de collaboration,
              vous pouvez ignorer ce message. Je ne vous recontacterai pas.
            </p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f9fafb;border-top:1px solid #e5e7eb;padding:20px 40px;text-align:center">
            <p style="margin:0;font-size:12px;color:#9ca3af">
              Immigration97 · contact@immigration97.com · +237 693 649 944
            </p>
            <p style="margin:8px 0 0;font-size:12px;color:#9ca3af">
              <a href="https://immigration97.com" style="color:#D4A843;text-decoration:none">immigration97.com</a>
            </p>
          </td>
        </tr>

      </table>
    </td>
  </tr>
</table>
</body>
</html>"""


def create_default_template(apps, schema_editor):
    OutreachTemplate = apps.get_model("outreach", "OutreachTemplate")
    OutreachTemplate.objects.get_or_create(
        name="Template Recruteur FR — Standard",
        defaults={
            "language": "fr",
            "subject": DEFAULT_SUBJECT,
            "body_text": DEFAULT_BODY_TEXT,
            "body_html": DEFAULT_BODY_HTML,
            "is_active": True,
        }
    )


def remove_default_template(apps, schema_editor):
    OutreachTemplate = apps.get_model("outreach", "OutreachTemplate")
    OutreachTemplate.objects.filter(name="Template Recruteur FR — Standard").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("outreach", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_template, remove_default_template),
    ]
