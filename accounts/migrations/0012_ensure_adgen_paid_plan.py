from django.db import migrations


ADGEN_FEATURES = [
    "50 campagnes / mois",
    "Tous les modules publicitaires",
    "Vidéos publicitaires IA 15s optimisées",
    "Templates premium pour WhatsApp, TikTok et Reels",
    "Export JSON + historique des campagnes",
    "Support prioritaire E-Shelle",
]


def ensure_adgen_paid_plan(apps, schema_editor):
    AppPlan = apps.get_model("accounts", "AppPlan")
    AppPlan.objects.filter(app_key="adgen", is_free=True).update(is_active=False)
    AppPlan.objects.filter(slug="adgen-free").update(is_active=False)
    AppPlan.objects.update_or_create(
        slug="adgen-pro",
        defaults={
            "app_key": "adgen",
            "name": "AdGen Pro",
            "level": "pro",
            "description": "Accès payant aux campagnes publicitaires IA et vidéos AdGen.",
            "price_xaf": 3000,
            "price_eur": 5,
            "duration_days": 30,
            "features": ADGEN_FEATURES,
            "is_free": False,
            "is_popular": True,
            "is_active": True,
            "order": 1,
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0011_disable_adgen_free_plan"),
    ]

    operations = [
        migrations.RunPython(ensure_adgen_paid_plan, noop_reverse),
    ]
