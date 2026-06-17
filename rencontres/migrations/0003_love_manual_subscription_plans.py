from django.db import migrations, models


def update_love_plans(apps, schema_editor):
    PlanPremiumRencontre = apps.get_model("rencontres", "PlanPremiumRencontre")
    plans = {
        "silver": {
            "prix_mensuel": 2,
            "prix_annuel": 2,
            "prix_xaf_mensuel": 1200,
            "prix_xaf_annuel": 1200,
            "duree_jours": 3,
            "likes_par_jour": -1,
            "super_likes_par_jour": 3,
            "messages_par_jour": -1,
            "peut_voir_qui_a_like": True,
            "peut_rembobiner": False,
            "boost_profil_par_semaine": 0,
            "photos_max": 8,
            "badge_premium": True,
            "filtre_avance": False,
            "sans_publicite": True,
            "mode_incognito": False,
            "stats_profil": False,
            "description": "Acces premium court pour tester E-Shelle Love pendant 3 jours.",
        },
        "gold": {
            "prix_mensuel": 4,
            "prix_annuel": 4,
            "prix_xaf_mensuel": 2500,
            "prix_xaf_annuel": 2500,
            "duree_jours": 10,
            "likes_par_jour": -1,
            "super_likes_par_jour": 10,
            "messages_par_jour": -1,
            "peut_voir_qui_a_like": True,
            "peut_rembobiner": True,
            "boost_profil_par_semaine": 1,
            "photos_max": 12,
            "badge_premium": True,
            "filtre_avance": True,
            "sans_publicite": True,
            "mode_incognito": True,
            "stats_profil": False,
            "description": "Acces premium 10 jours pour discuter, matcher et utiliser les filtres avances.",
        },
        "platinum": {
            "prix_mensuel": 8,
            "prix_annuel": 8,
            "prix_xaf_mensuel": 4900,
            "prix_xaf_annuel": 4900,
            "duree_jours": 30,
            "likes_par_jour": -1,
            "super_likes_par_jour": -1,
            "messages_par_jour": -1,
            "peut_voir_qui_a_like": True,
            "peut_rembobiner": True,
            "boost_profil_par_semaine": 3,
            "photos_max": 12,
            "badge_premium": True,
            "filtre_avance": True,
            "sans_publicite": True,
            "mode_incognito": True,
            "stats_profil": True,
            "description": "Acces premium complet pendant 1 mois.",
        },
    }
    for nom, values in plans.items():
        PlanPremiumRencontre.objects.update_or_create(nom=nom, defaults=values)


class Migration(migrations.Migration):
    dependencies = [
        ("rencontres", "0002_plans_initiaux"),
    ]

    operations = [
        migrations.AddField(
            model_name="planpremiumrencontre",
            name="duree_jours",
            field=models.PositiveSmallIntegerField(default=30),
        ),
        migrations.RunPython(update_love_plans, migrations.RunPython.noop),
    ]
