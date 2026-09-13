from django.db import migrations


def seed(apps, schema_editor):
    Plan = apps.get_model("accounts", "AppPlan")
    rows = [
        ("essentiel", "Essentiel", 3000, "5.00", "starter", 20, 5, 3000),
        ("createur", "Créateur", 10000, "16.00", "pro", 100, 25, 15000),
        ("business", "Business", 25000, "40.00", "enterprise", 300, 80, 45000),
    ]
    for order, (slug, name, price, eur, level, text, video, voice) in enumerate(rows, 1):
        Plan.objects.using(schema_editor.connection.alias).get_or_create(
            slug=f"adgen-studio-{slug}", defaults=dict(
                app_key="adgen", name=f"AdGen Studio {name}", level=level,
                price_xaf=price, price_eur=eur, duration_days=30, is_free=False,
                is_active=True, is_popular=slug == "createur", order=order,
                description="Textes, voix-off et montages publicitaires réunis. Quotas sur 30 jours glissants.",
                features=[f"{text} lots de textes / 30 jours", f"{video} montages photo de 15 secondes / 30 jours",
                          f"{voice:,} caractères de voix-off standard / 30 jours".replace(",", " "),
                          f"{video} ambiances sonores simples / 30 jours", "Bibliothèque audio et campagnes communes",
                          "Téléchargements et corrections manuelles sans nouvelle génération",
                          "Scènes vidéo IA externes et clonage vocal non inclus", "Budget de diffusion publicitaire non inclus"],
            ))
    # Preserve legacy rows and subscriptions. Hide only from new purchases.
    Plan.objects.using(schema_editor.connection.alias).filter(
        slug__in=["adgen-starter", "adgen-pro", "adgen-business"]).update(is_active=False)


def reverse_seed(apps, schema_editor):
    Plan = apps.get_model("accounts", "AppPlan")
    Plan.objects.using(schema_editor.connection.alias).filter(slug__in=[
        "adgen-studio-essentiel", "adgen-studio-createur", "adgen-studio-business"]).update(is_active=False)
    Plan.objects.using(schema_editor.connection.alias).filter(
        slug__in=["adgen-starter", "adgen-pro", "adgen-business"]).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [("accounts", "0013_adgen_profitable_paid_plans")]
    operations = [migrations.RunPython(seed, reverse_seed)]
