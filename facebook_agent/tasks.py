"""
Tâches Celery pour l'agent Facebook E-Shelle.
Automatise la génération et publication de posts selon un planning.
"""

import logging
import time
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger("facebook_agent")


# ------------------------------------------------------------------ #
# Tâche principale : générer et publier un post                       #
# ------------------------------------------------------------------ #

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def generate_and_publish_post(self, section: str, page_config_id: int = None, approved_manual: bool = False):
    """
    Génère un post IA pour une section et le publie sur Facebook.
    Retry automatique 3 fois en cas d'échec.
    """
    from facebook_agent.models import (
        FacebookPageConfig, ScheduledPost, PublishedPost, AgentLog
    )
    from facebook_agent.agents import run_agent_for_section
    from facebook_agent.facebook_api import FacebookAPIClient, FacebookAPIError

    start_time = time.time()
    log_details = {"section": section, "page_config_id": page_config_id}

    from django.conf import settings
    if not approved_manual and not getattr(settings, "FACEBOOK_AGENT_AUTO_PUBLISH_ENABLED", False):
        return {"status": "disabled", "message": "La publication Facebook automatique est désactivée."}

    try:
        # Récupérer la config de la page
        if page_config_id:
            config = FacebookPageConfig.objects.get(id=page_config_id, is_active=True)
        else:
            config = FacebookPageConfig.objects.filter(is_active=True).first()

        if not config:
            logger.error("[Task] Aucune configuration de page Facebook active")
            AgentLog.objects.create(
                section=section,
                action="agent_run",
                level="error",
                message="Aucune configuration de page Facebook active",
                details=log_details,
            )
            return {"status": "error", "message": "No page config"}

        # Vérifier la validité du token
        if not config.is_token_valid():
            logger.warning(f"[Task] Token expiré pour la page {config.page_name}")
            AgentLog.objects.create(
                section=section,
                action="token_check",
                level="warning",
                message=f"Token expiré pour {config.page_name}",
                details=log_details,
            )
            return {"status": "error", "message": "Token expired"}

        # Générer le contenu via l'agent IA
        logger.info(f"[Task] Génération contenu pour section '{section}'")
        AgentLog.objects.create(
            section=section,
            action="generate_content",
            level="info",
            message=f"Démarrage génération contenu pour '{section}'",
            details=log_details,
        )

        result = run_agent_for_section(section)

        if not result or not result.get("content"):
            logger.error(f"[Task] L'agent n'a pas produit de contenu pour '{section}'")
            AgentLog.objects.create(
                section=section,
                action="generate_content",
                level="error",
                message="L'agent n'a pas produit de contenu",
                details=log_details,
            )
            return {"status": "error", "message": "No content generated"}

        max_daily_posts = max(1, int(getattr(settings, "FACEBOOK_AGENT_MAX_POSTS_PER_DAY", 3)))
        published_today = PublishedPost.objects.filter(published_at__date=timezone.localdate()).count()
        if published_today >= max_daily_posts:
            return {"status": "daily_limit", "message": "Limite quotidienne de publications atteinte."}

        content = result["content"]
        image_url = result.get("image_url", "")
        link_url = result.get("link_url", "")
        tokens_used = result.get("tokens_used", 0)

        # Vérifier si approbation requise
        from facebook_agent.models import ContentRule
        rule = ContentRule.objects.filter(section=section, is_active=True).first()

        # Publier sur Facebook
        fb_client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)

        logger.info(f"[Task] Publication sur Facebook page '{config.page_name}'")
        fb_result = fb_client.publish_post(
            message=content,
            image_url=image_url,
            link_url=link_url,
        )

        facebook_post_id = fb_result.get("id", "")

        # Enregistrer le post publié
        published = PublishedPost.objects.create(
            page_config=config,
            section=section,
            facebook_post_id=facebook_post_id,
            content=content,
            image_url=image_url,
            link_url=link_url,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        AgentLog.objects.create(
            section=section,
            action="publish_post",
            level="success",
            message=f"Post publié avec succès: {facebook_post_id}",
            details={
                **log_details,
                "facebook_post_id": facebook_post_id,
                "content_preview": content[:100],
            },
            duration_ms=duration_ms,
            tokens_used=tokens_used,
        )

        # Mettre à jour les stats journalières
        update_daily_stats.delay(section)

        logger.info(f"[Task] Post publié avec succès — ID Facebook: {facebook_post_id}")
        return {
            "status": "success",
            "facebook_post_id": facebook_post_id,
            "section": section,
            "tokens_used": tokens_used,
        }

    except FacebookAPIError as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(f"[Task] Erreur Facebook API pour '{section}': {exc}")
        AgentLog.objects.create(
            section=section,
            action="publish_post",
            level="error",
            message=f"Erreur Facebook API: {exc}",
            details={**log_details, "error_code": exc.code},
            duration_ms=duration_ms,
        )
        # Retry si erreur temporaire (pas d'erreur d'auth)
        if exc.code not in (190, 200, 10):  # Token invalide ou permission refusée
            raise self.retry(exc=exc)
        return {"status": "error", "message": str(exc)}

    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.exception(f"[Task] Erreur inattendue pour '{section}': {exc}")
        AgentLog.objects.create(
            section=section,
            action="agent_run",
            level="error",
            message=f"Erreur inattendue: {exc}",
            details=log_details,
            duration_ms=duration_ms,
        )
        raise self.retry(exc=exc)


# ------------------------------------------------------------------ #
# Tâche : publier un post planifié                                    #
# ------------------------------------------------------------------ #

@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def publish_scheduled_post(self, scheduled_post_id: str):
    """Publie un post qui était planifié (ScheduledPost)."""
    from facebook_agent.models import ScheduledPost, PublishedPost, AgentLog
    from facebook_agent.facebook_api import FacebookAPIClient, FacebookAPIError
    from django.conf import settings
    try:
        post = ScheduledPost.objects.get(id=scheduled_post_id)

        if post.status == "publie":
            return {"status": "already_published"}

        if post.requires_approval and post.status != "approuve":
            logger.info(f"[Task] Post {scheduled_post_id} en attente d'approbation")
            return {"status": "pending_approval"}

        max_daily_posts = max(1, int(getattr(settings, "FACEBOOK_AGENT_MAX_POSTS_PER_DAY", 3)))
        if PublishedPost.objects.filter(published_at__date=timezone.localdate()).count() >= max_daily_posts:
            post.error_message = "Limite quotidienne de publications atteinte."
            post.save(update_fields=["error_message", "updated_at"])
            return {"status": "daily_limit"}

        config = post.page_config
        fb_client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)

        fb_result = fb_client.publish_post(
            message=post.content,
            image_url=post.image_url,
            link_url="" if post.source_object_type == "facebook_first_comment" else post.link_url,
        )

        facebook_post_id = fb_result.get("id", "")

        if post.source_object_type == "facebook_first_comment" and post.link_url:
            try:
                fb_client.publish_comment(facebook_post_id, post.link_url)
            except FacebookAPIError as comment_error:
                AgentLog.objects.create(
                    section=post.section, action="publish_post", level="warning",
                    message=f"Post publié, mais premier commentaire non publié: {comment_error}",
                    details={"scheduled_post_id": str(scheduled_post_id), "facebook_post_id": facebook_post_id},
                )

        PublishedPost.objects.create(
            scheduled_post=post,
            page_config=config,
            section=post.section,
            facebook_post_id=facebook_post_id,
            content=post.content,
            image_url=post.image_url,
            link_url=post.link_url,
        )

        post.status = "publie"
        post.save(update_fields=["status", "updated_at"])

        AgentLog.objects.create(
            section=post.section,
            action="publish_post",
            level="success",
            message=f"Post planifié publié: {facebook_post_id}",
            details={"scheduled_post_id": str(scheduled_post_id), "facebook_post_id": facebook_post_id},
        )

        return {"status": "success", "facebook_post_id": facebook_post_id}

    except ScheduledPost.DoesNotExist:
        logger.error(f"[Task] ScheduledPost {scheduled_post_id} introuvable")
        return {"status": "error", "message": "Post not found"}
    except Exception as exc:
        logger.exception(f"[Task] Erreur publication post planifié {scheduled_post_id}: {exc}")
        try:
            post = ScheduledPost.objects.get(id=scheduled_post_id)
            post.retry_count += 1
            post.error_message = str(exc)
            post.save(update_fields=["retry_count", "error_message", "updated_at"])
        except Exception:
            pass
        raise self.retry(exc=exc)


# ------------------------------------------------------------------ #
# Tâche : vérifier et traiter les posts planifiés en attente          #
# ------------------------------------------------------------------ #

@shared_task
def process_pending_scheduled_posts():
    """Vérifie les posts planifiés et les publie si l'heure est venue."""
    from facebook_agent.models import ScheduledPost
    from django.conf import settings

    auto_enabled = getattr(settings, "FACEBOOK_AGENT_AUTO_PUBLISH_ENABLED", False)
    allowed_statuses = ("en_attente", "approuve") if auto_enabled else ("approuve",)
    now = timezone.now()
    pending = ScheduledPost.objects.filter(
        status__in=allowed_statuses,
        scheduled_at__lte=now,
        retry_count__lt=3,
    )

    count = pending.count()
    if count:
        logger.info(f"[Task] {count} posts planifiés à traiter")
        for post in pending:
            publish_scheduled_post.delay(str(post.id))

    return {"processed": count}


@shared_task
def create_daily_summary_draft():
    """Create one daily summary draft for review; never publish from this task."""
    from facebook_agent.models import FacebookPageConfig, ScheduledPost, PublishedPost
    from facebook_agent.prompts import generate_daily_summary_draft

    today = timezone.localdate()
    source_id = f"daily:{today.isoformat()}"
    if not FacebookPageConfig.objects.filter(is_active=True).exists():
        return {"status": "no_active_page"}
    if ScheduledPost.objects.filter(source_object_type="facebook_first_comment", source_object_id=source_id).exists():
        return {"status": "already_created"}

    from django.conf import settings
    max_daily = max(1, int(getattr(settings, "FACEBOOK_AGENT_MAX_POSTS_PER_DAY", 3)))
    occupied = ScheduledPost.objects.filter(scheduled_at__date=today).filter(
        status__in=("en_attente", "approuve", "publie")
    ).count()
    occupied += PublishedPost.objects.filter(published_at__date=today).exclude(
        scheduled_post__isnull=False
    ).count()
    if occupied >= max_daily:
        return {"status": "daily_limit"}

    draft = generate_daily_summary_draft()
    scheduled_at = timezone.localtime().replace(hour=18, minute=0, second=0, microsecond=0)
    if scheduled_at <= timezone.now():
        scheduled_at += timedelta(days=1)
    config = FacebookPageConfig.objects.filter(is_active=True).first()
    post = ScheduledPost.objects.create(
        page_config=config, section="general", title=f"Résumé E-Shelle du {today:%d/%m/%Y}",
        content=draft["text"], link_url=draft.get("first_comment", "https://e-shelle.com/"),
        scheduled_at=scheduled_at, status="en_attente", requires_approval=True,
        ai_generated=True, source_object_id=source_id,
        source_object_type="facebook_first_comment",
    )
    return {"status": "created", "draft_id": str(post.id)}


# ------------------------------------------------------------------ #
# Tâche : synchroniser les statistiques des posts                     #
# ------------------------------------------------------------------ #

@shared_task
def sync_post_stats(published_post_id: str = None):
    """Met à jour les statistiques (likes, commentaires, partages) des posts récents."""
    from facebook_agent.models import PublishedPost, FacebookPageConfig
    from facebook_agent.facebook_api import FacebookAPIClient

    # Sync les posts des 7 derniers jours si pas d'ID spécifique
    if published_post_id:
        posts = PublishedPost.objects.filter(id=published_post_id)
    else:
        cutoff = timezone.now() - timedelta(days=7)
        posts = PublishedPost.objects.filter(published_at__gte=cutoff)

    updated = 0
    config = FacebookPageConfig.objects.filter(is_active=True).first()
    if not config:
        return {"updated": 0}

    fb_client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)

    for post in posts:
        try:
            stats = fb_client.get_post_insights(post.facebook_post_id)
            post.likes_count = stats.get("likes", 0)
            post.comments_count = stats.get("comments", 0)
            post.shares_count = stats.get("shares", 0)
            post.stats_updated_at = timezone.now()
            post.save(update_fields=[
                "likes_count", "comments_count", "shares_count", "stats_updated_at"
            ])
            updated += 1
        except Exception as e:
            logger.warning(f"[Task] Erreur sync stats post {post.facebook_post_id}: {e}")

    logger.info(f"[Task] Stats synchronisées pour {updated} posts")
    return {"updated": updated}


# ------------------------------------------------------------------ #
# Tâche : mettre à jour les stats journalières                        #
# ------------------------------------------------------------------ #

@shared_task
def update_daily_stats(section: str = None):
    """Met à jour les statistiques journalières agrégées."""
    from facebook_agent.models import AgentStats, PublishedPost, AgentLog
    from django.db.models import Sum, Count
    from django.utils.timezone import now

    today = now().date()
    stats, _ = AgentStats.objects.get_or_create(date=today)

    # Compter les posts du jour
    today_posts = PublishedPost.objects.filter(published_at__date=today)
    stats.total_posts_published = today_posts.count()

    # Agrégations
    agg = today_posts.aggregate(
        total_likes=Sum("likes_count"),
        total_comments=Sum("comments_count"),
        total_reach=Sum("reach"),
    )
    stats.total_likes = agg["total_likes"] or 0
    stats.total_comments = agg["total_comments"] or 0
    stats.total_reach = agg["total_reach"] or 0

    # Posts par section
    posts_by_section = {}
    for item in today_posts.values("section").annotate(count=Count("id")):
        posts_by_section[item["section"]] = item["count"]
    stats.posts_by_section = posts_by_section

    # Tokens IA utilisés
    token_agg = AgentLog.objects.filter(
        created_at__date=today
    ).aggregate(total=Sum("tokens_used"))
    stats.total_tokens_used = token_agg["total"] or 0

    # Posts générés et échoués
    stats.total_posts_generated = AgentLog.objects.filter(
        created_at__date=today, action="generate_content", level="success"
    ).count()
    stats.total_posts_failed = AgentLog.objects.filter(
        created_at__date=today, action="publish_post", level="error"
    ).count()

    stats.save()
    return {"date": str(today), "published": stats.total_posts_published}


# ------------------------------------------------------------------ #
# Tâche : vérifier la validité du token                               #
# ------------------------------------------------------------------ #

@shared_task
def check_token_validity():
    """Vérifie que le token d'accès Facebook est toujours valide."""
    from facebook_agent.models import FacebookPageConfig, AgentLog
    from facebook_agent.facebook_api import FacebookAPIClient

    configs = FacebookPageConfig.objects.filter(is_active=True)

    for config in configs:
        fb_client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
        token_info = fb_client.verify_token()

        if not token_info.get("is_valid"):
            AgentLog.objects.create(
                section="",
                action="token_check",
                level="error",
                message=f"Token INVALIDE pour la page '{config.page_name}' — action requise!",
                details={"page_id": config.page_id, "page_name": config.page_name},
            )
            logger.critical(f"[Task] TOKEN INVALIDE pour {config.page_name} — publication impossible!")
        else:
            expires_at = token_info.get("expires_at")
            AgentLog.objects.create(
                section="",
                action="token_check",
                level="success",
                message=f"Token valide pour '{config.page_name}'",
                details={
                    "page_id": config.page_id,
                    "expires_at": str(expires_at) if expires_at else "permanent",
                },
            )
            logger.info(f"[Task] Token valide pour {config.page_name}")

    return {"checked": configs.count()}


# ------------------------------------------------------------------ #
# Planification Celery Beat (Beat Schedule)                           #
# ------------------------------------------------------------------ #

# Ces tâches sont configurées dans settings.py via CELERY_BEAT_SCHEDULE
# Voir edu_cm/settings.py pour le planning complet
