from django.db import migrations


ADGEN_PLANS = [
    {
        "slug": "adgen-starter",
        "defaults": {
            "app_key": "adgen",
            "name": "AdGen Starter",
            "level": "starter",
            "description": "Pour tester le marketing IA sans vendre a perte: campagnes et videos rapides locales.",
            "price_xaf": 3000,
            "price_eur": 5,
            "duration_days": 30,
            "features": [
                "30 campagnes / mois",
                "10 videos publicitaires rapides / mois",
                "Videos 15s optimisees pour WhatsApp, TikTok et Reels",
                "Templates premium rapides",
                "Export JSON + historique des campagnes",
                "Support WhatsApp",
                "Credits Sora non inclus",
            ],
            "is_free": False,
            "is_popular": False,
            "is_active": True,
            "order": 1,
        },
    },
    {
        "slug": "adgen-pro",
        "defaults": {
            "app_key": "adgen",
            "name": "AdGen Pro",
            "level": "pro",
            "description": "Le forfait rentable pour publier regulierement des publicites video.",
            "price_xaf": 10000,
            "price_eur": 16,
            "duration_days": 30,
            "features": [
                "150 campagnes / mois",
                "50 videos publicitaires rapides / mois",
                "Tous les modules publicitaires",
                "Videos 15s optimisees pour WhatsApp, TikTok et Reels",
                "Templates premium + styles avances",
                "Export JSON + historique des campagnes",
                "Support prioritaire E-Shelle",
                "Credits Sora non inclus",
            ],
            "is_free": False,
            "is_popular": True,
            "is_active": True,
            "order": 2,
        },
    },
    {
        "slug": "adgen-business",
        "defaults": {
            "app_key": "adgen",
            "name": "AdGen Business",
            "level": "enterprise",
            "description": "Pour agences, vendeurs actifs et equipes qui generent beaucoup de visuels.",
            "price_xaf": 25000,
            "price_eur": 40,
            "duration_days": 30,
            "features": [
                "500 campagnes / mois",
                "150 videos publicitaires rapides / mois",
                "Tous les modules publicitaires",
                "Templates premium + styles avances",
                "Export JSON + historique des campagnes",
                "Priorite de support",
                "Credits Sora non inclus",
            ],
            "is_free": False,
            "is_popular": False,
            "is_active": True,
            "order": 3,
        },
    },
]


def apply_adgen_plans(apps, schema_editor):
    AppPlan = apps.get_model("accounts", "AppPlan")
    AppPlan.objects.filter(app_key="adgen", is_free=True).update(is_active=False)
    AppPlan.objects.filter(app_key="adgen", level__in=["free", "trial"]).update(is_active=False)
    for plan in ADGEN_PLANS:
        AppPlan.objects.update_or_create(slug=plan["slug"], defaults=plan["defaults"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_ensure_adgen_paid_plan"),
    ]

    operations = [
        migrations.RunPython(apply_adgen_plans, noop_reverse),
    ]
