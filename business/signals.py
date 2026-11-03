from django.apps import apps
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import ensure_business_for_object


def _model(app_label, model_name):
    try:
        return apps.get_model(app_label, model_name)
    except LookupError:
        return None


Restaurant = _model("resto", "Restaurant")
DepotGaz = _model("gaz", "DepotGaz")
Pressing = _model("pressing", "Pressing")
ProfessionnelSante = _model("sante", "ProfessionnelSante")
ProduitSante = _model("sante", "ProduitSante")
OffreJob = _model("jobs", "OffreJob")
ActeurAgro = _model("agro", "ActeurAgro")
ProfilVendeur = _model("annonces_cam", "ProfilVendeur")
Annonce = _model("annonces_cam", "Annonce")
ProfilArtisan = _model("artisans", "ProfilArtisan")
Vehicule = _model("auto_cameroun", "Vehicule")
Bien = _model("immobilier_cameroun", "Bien")


if Restaurant:
    @receiver(post_save, sender=Restaurant, dispatch_uid="business_sync_resto_restaurant")
    def sync_restaurant_business(sender, instance, **kwargs):
        ensure_business_for_object(instance, "resto")


if DepotGaz:
    @receiver(post_save, sender=DepotGaz, dispatch_uid="business_sync_gaz_depot")
    def sync_depot_gaz_business(sender, instance, **kwargs):
        ensure_business_for_object(instance, "gaz")


if Pressing:
    @receiver(post_save, sender=Pressing, dispatch_uid="business_sync_pressing")
    def sync_pressing_business(sender, instance, **kwargs):
        ensure_business_for_object(instance, "pressing")


if ProfessionnelSante:
    @receiver(post_save, sender=ProfessionnelSante, dispatch_uid="business_sync_sante_pro")
    def sync_sante_pro_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "sante",
            {
                "owner": instance.auteur,
                "name": instance.nom,
                "city": getattr(instance.ville, "nom", ""),
                "district": instance.quartier,
                "description": instance.description,
            },
        )


if ProduitSante:
    @receiver(post_save, sender=ProduitSante, dispatch_uid="business_sync_sante_product")
    def sync_sante_product_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "sante",
            {
                "owner": instance.auteur,
                "name": instance.vendeur_nom or instance.titre,
                "city": getattr(instance.ville, "nom", ""),
                "description": instance.description,
            },
        )


if OffreJob:
    @receiver(post_save, sender=OffreJob, dispatch_uid="business_sync_jobs_offer")
    def sync_job_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "jobs",
            {
                "owner": instance.auteur,
                "name": instance.entreprise,
                "city": getattr(instance.ville, "nom", ""),
                "district": instance.quartier,
                "description": instance.description,
            },
        )


if ActeurAgro:
    @receiver(post_save, sender=ActeurAgro, dispatch_uid="business_sync_agro_actor")
    def sync_agro_actor_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "agro",
            {
                "owner": instance.user,
                "name": instance.nom_entreprise,
                "city": instance.ville,
                "district": instance.region,
                "phone": instance.telephone,
                "whatsapp": instance.whatsapp or instance.telephone,
                "description": instance.description,
            },
        )


if ProfilVendeur:
    @receiver(post_save, sender=ProfilVendeur, dispatch_uid="business_sync_market_seller")
    def sync_market_seller_business(sender, instance, **kwargs):
        display_name = instance.nom_boutique or instance.user.get_full_name() or instance.user.username
        ensure_business_for_object(
            instance,
            "market",
            {
                "owner": instance.user,
                "name": display_name,
                "city": instance.ville,
                "phone": instance.telephone,
                "whatsapp": instance.whatsapp or instance.telephone,
                "description": instance.description_boutique,
                "is_verified": instance.est_verifie,
            },
        )


if Annonce:
    @receiver(post_save, sender=Annonce, dispatch_uid="business_sync_market_announcement")
    def sync_market_announcement_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "market",
            {
                "owner": instance.vendeur,
                "name": instance.titre,
                "city": instance.ville,
                "phone": instance.telephone_contact,
                "whatsapp": instance.whatsapp_contact or instance.telephone_contact,
                "description": instance.description,
            },
        )


if ProfilArtisan:
    @receiver(post_save, sender=ProfilArtisan, dispatch_uid="business_sync_artisan")
    def sync_artisan_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "services",
            {
                "owner": instance.user,
                "name": instance.nom_public,
                "city": getattr(instance.ville, "nom", ""),
                "district": instance.quartier,
                "phone": instance.telephone,
                "whatsapp": instance.whatsapp or instance.telephone,
                "description": instance.description,
                "is_verified": instance.est_verifie,
            },
        )


if Vehicule:
    @receiver(post_save, sender=Vehicule, dispatch_uid="business_sync_auto_vehicle")
    def sync_vehicle_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "auto",
            {
                "owner": instance.proprietaire,
                "name": instance.titre,
                "city": instance.ville,
                "district": instance.quartier,
                "description": instance.description,
            },
        )


if Bien:
    @receiver(post_save, sender=Bien, dispatch_uid="business_sync_immo_bien")
    def sync_bien_business(sender, instance, **kwargs):
        ensure_business_for_object(
            instance,
            "immobilier",
            {
                "owner": instance.proprietaire,
                "name": instance.titre,
                "city": instance.ville,
                "district": instance.quartier,
                "description": instance.description,
            },
        )


from django.db import transaction
from django.conf import settings
from business.models import BusinessProfile

try:
    from facebook_agent.tasks import share_premium_facebook_task
    HAS_CELERY = True
except ImportError:
    HAS_CELERY = False

@receiver(post_save, sender=BusinessProfile)
def auto_share_premium_to_facebook(sender, instance, created, **kwargs):
    update_fields = kwargs.get('update_fields')
    if update_fields and any(f in update_fields for f in ['facebook_shared_at', 'last_facebook_post_id']):
        return
    if not getattr(settings, 'FACEBOOK_AUTO_SHARE_ENABLED', True):
        return
    from core.services.facebook_auto_share import should_share
    if not should_share(instance):
        return
    if HAS_CELERY:
        transaction.on_commit(lambda: share_premium_facebook_task.delay(instance.pk))
    else:
        from core.services.facebook_auto_share import trigger_async_share_premium
        transaction.on_commit(lambda: trigger_async_share_premium(instance.pk))
