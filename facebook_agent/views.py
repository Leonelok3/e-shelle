"""
Vues du dashboard Facebook Agent E-Shelle.
Accessible uniquement aux administrateurs et superadmins.
"""

import json
import re
from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from .models import (
    FacebookPageConfig,
    ContentRule,
    ScheduledPost,
    PublishedPost,
    AgentLog,
    AgentStats,
)


def staff_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


# ------------------------------------------------------------------ #
# Dashboard principal                                                 #
# ------------------------------------------------------------------ #

@staff_required
def dashboard(request):
    """Vue principale du dashboard de l'agent Facebook."""
    from django.conf import settings
    from business.models import BusinessProfile
    from business.models import BusinessCatalogItem
    from business.models import BusinessLeadEvent
    from njangi.models import NjangiAchatGroupe

    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)

    # Stats globales
    page_config = FacebookPageConfig.objects.filter(is_active=True).first()
    total_published = PublishedPost.objects.count()
    published_today = PublishedPost.objects.filter(published_at__date=today).count()
    published_week = PublishedPost.objects.filter(published_at__gte=week_ago).count()
    pending_posts = ScheduledPost.objects.filter(status__in=("en_attente", "approuve")).count()
    failed_today = AgentLog.objects.filter(
        created_at__date=today, action="publish_post", level="error"
    ).count()

    # Stats journalières des 7 derniers jours
    daily_stats = AgentStats.objects.filter(
        date__gte=week_ago.date()
    ).order_by("date")

    # Graphique: posts publiés par jour
    chart_labels = []
    chart_published = []
    chart_likes = []
    for stat in daily_stats:
        chart_labels.append(stat.date.strftime("%d/%m"))
        chart_published.append(stat.total_posts_published)
        chart_likes.append(stat.total_likes)

    # Posts récents publiés
    recent_published = PublishedPost.objects.select_related("page_config").order_by("-published_at")[:10]

    # Logs récents
    recent_logs = AgentLog.objects.order_by("-created_at")[:20]

    # Posts planifiés à venir
    upcoming_posts = ScheduledPost.objects.filter(
        status__in=("en_attente", "approuve"),
        scheduled_at__gte=now,
    ).order_by("scheduled_at")[:5]

    # Stats par section (7 derniers jours)
    from django.db.models import Count
    section_stats = (
        PublishedPost.objects
        .filter(published_at__gte=week_ago)
        .values("section")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    campaign_stats = {
        "views": BusinessLeadEvent.objects.filter(
            source="facebook", event_type=BusinessLeadEvent.EventType.VIEW,
            created_at__gte=week_ago,
        ).count(),
        "whatsapp": BusinessLeadEvent.objects.filter(
            source="facebook", event_type=BusinessLeadEvent.EventType.WHATSAPP,
            created_at__gte=week_ago,
        ).count(),
        "orders": BusinessLeadEvent.objects.filter(
            source="facebook", event_type=BusinessLeadEvent.EventType.ORDER,
            created_at__gte=week_ago,
        ).count(),
    }

    # Page insights
    page_insights = {}
    if page_config:
        try:
            from .facebook_api import FacebookAPIClient
            client = FacebookAPIClient(page_config.page_access_token, page_config.page_id,
                                       page_config.app_id, page_config.app_secret)
            page_insights = client.get_page_insights()
        except Exception:
            pass

    context = {
        "page_title": "Dashboard Facebook Agent",
        "page_config": page_config,
        "page_insights": page_insights,
        "total_published": total_published,
        "published_today": published_today,
        "published_week": published_week,
        "pending_posts": pending_posts,
        "failed_today": failed_today,
        "chart_labels": json.dumps(chart_labels),
        "chart_published": json.dumps(chart_published),
        "chart_likes": json.dumps(chart_likes),
        "recent_published": recent_published,
        "recent_logs": recent_logs,
        "upcoming_posts": upcoming_posts,
        "section_stats": section_stats,
        "content_rules": ContentRule.objects.all().order_by("section"),
        "business_profiles": BusinessProfile.objects.filter(is_active=True).order_by("name")[:100],
        "catalog_products": BusinessCatalogItem.objects.filter(
            is_active=True, item_type=BusinessCatalogItem.ItemType.PRODUCT,
            business__is_active=True,
        ).select_related("business").order_by("-created_at")[:100],
        "njangi_groups": NjangiAchatGroupe.objects.filter(
            status=NjangiAchatGroupe.Status.OPEN,
        ).select_related("product", "product__business").order_by("date_cloture")[:100],
        "campaign_stats": campaign_stats,
        "auto_publish_enabled": getattr(settings, "FACEBOOK_AGENT_AUTO_PUBLISH_ENABLED", False),
        "daily_post_limit": getattr(settings, "FACEBOOK_AGENT_MAX_POSTS_PER_DAY", 3),
    }
    return render(request, "facebook_agent/dashboard.html", context)


# ------------------------------------------------------------------ #
# Publication manuelle immédiate                                      #
# ------------------------------------------------------------------ #

@staff_required
@require_POST
def publish_now(request):
    """Déclenche immédiatement la publication d'un post pour une section."""
    section = request.POST.get("section", "general")
    page_config_id = request.POST.get("page_config_id")

    try:
        from .tasks import generate_and_publish_post
        task = generate_and_publish_post.delay(
            section=section,
            page_config_id=int(page_config_id) if page_config_id else None,
            approved_manual=True,
        )
        messages.success(
            request,
            f"Publication lancée pour la section '{section}'. Tâche ID: {task.id}"
        )
    except Exception as e:
        messages.error(request, f"Erreur lors du lancement: {e}")

    return redirect("facebook_agent:dashboard")


# ------------------------------------------------------------------ #
# Publication manuelle via API (AJAX)                                 #
# ------------------------------------------------------------------ #

@staff_required
@require_POST
def publish_now_ajax(request):
    """API AJAX pour déclencher une publication."""
    try:
        data = json.loads(request.body)
        section = data.get("section", "general")
        page_config_id = data.get("page_config_id")

        from .tasks import generate_and_publish_post
        task = generate_and_publish_post.delay(
            section=section,
            page_config_id=int(page_config_id) if page_config_id else None,
            approved_manual=True,
        )
        return JsonResponse({
            "status": "success",
            "message": f"Publication lancée pour '{section}'",
            "task_id": task.id,
        })
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


# ------------------------------------------------------------------ #
# Liste des posts publiés                                             #
# ------------------------------------------------------------------ #

@staff_required
def published_posts(request):
    """Liste paginée des posts publiés."""
    from django.core.paginator import Paginator

    section_filter = request.GET.get("section", "")
    posts_qs = PublishedPost.objects.select_related("page_config").order_by("-published_at")

    if section_filter:
        posts_qs = posts_qs.filter(section=section_filter)

    paginator = Paginator(posts_qs, 20)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    sections = ContentRule.SECTION_CHOICES

    context = {
        "page_title": "Posts Publiés",
        "page_obj": page_obj,
        "sections": sections,
        "section_filter": section_filter,
        "total_count": posts_qs.count(),
    }
    return render(request, "facebook_agent/published_posts.html", context)


# ------------------------------------------------------------------ #
# Liste des posts planifiés                                           #
# ------------------------------------------------------------------ #

@staff_required
def scheduled_posts(request):
    """Liste des posts planifiés."""
    posts = ScheduledPost.objects.select_related("page_config").order_by("scheduled_at")
    sections = ContentRule.SECTION_CHOICES

    context = {
        "page_title": "Posts Planifiés",
        "posts": posts,
        "sections": sections,
        "now": timezone.now(),
    }
    return render(request, "facebook_agent/scheduled_posts.html", context)


# ------------------------------------------------------------------ #
# Créer un post planifié manuellement                                 #
# ------------------------------------------------------------------ #

@staff_required
def create_scheduled_post(request):
    """Créer un post planifié manuellement."""
    if request.method == "POST":
        page_config_id = request.POST.get("page_config")
        section = request.POST.get("section")
        title = request.POST.get("title")
        content = request.POST.get("content")
        scheduled_at = request.POST.get("scheduled_at")
        image_url = request.POST.get("image_url", "")
        link_url = request.POST.get("link_url", "")
        requires_approval = request.POST.get("requires_approval") == "on"

        try:
            page_config = FacebookPageConfig.objects.get(id=page_config_id)
            from django.utils.dateparse import parse_datetime
            scheduled_dt = parse_datetime(scheduled_at)
            if scheduled_dt and timezone.is_naive(scheduled_dt):
                scheduled_dt = timezone.make_aware(scheduled_dt)

            ScheduledPost.objects.create(
                page_config=page_config,
                section=section,
                title=title,
                content=content,
                image_url=image_url,
                link_url=link_url,
                scheduled_at=scheduled_dt,
                requires_approval=requires_approval,
                ai_generated=False,
            )
            messages.success(request, f"Post planifié créé avec succès pour le {scheduled_dt.strftime('%d/%m/%Y à %H:%M')}")
            return redirect("facebook_agent:scheduled_posts")
        except Exception as e:
            messages.error(request, f"Erreur: {e}")

    page_configs = FacebookPageConfig.objects.filter(is_active=True)
    sections = ContentRule.SECTION_CHOICES

    context = {
        "page_title": "Créer un Post Planifié",
        "page_configs": page_configs,
        "sections": sections,
    }
    return render(request, "facebook_agent/create_scheduled_post.html", context)


# ------------------------------------------------------------------ #
# Générer un aperçu de contenu IA                                     #
# ------------------------------------------------------------------ #

@staff_required
@require_POST
def preview_ai_content(request):
    """Génère un aperçu du contenu IA sans publier."""
    try:
        data = json.loads(request.body)
        section = data.get("section", "general")

        from .agents import run_agent_for_section
        result = run_agent_for_section(section)

        if result:
            return JsonResponse({
                "status": "success",
                "content": result.get("content", ""),
                "section": section,
                "tokens_used": result.get("tokens_used", 0),
            })
        return JsonResponse({"status": "error", "message": "Aucun contenu généré"}, status=500)
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@staff_required
@require_POST
def preview_business_created(request):
    """Prepare a new-business post draft without publishing or saving it."""
    try:
        data = json.loads(request.body)
        business_id = data.get("business_id")
        if not business_id:
            return JsonResponse({"status": "error", "message": "Choisissez une fiche business."}, status=400)

        from business.models import BusinessProfile
        business = get_object_or_404(
            BusinessProfile.objects.filter(is_active=True), pk=business_id
        )
        from .prompts import generate_business_created_draft
        draft = generate_business_created_draft(business)
        return JsonResponse({"status": "success", **draft})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@staff_required
@require_POST
def preview_marketing_draft(request):
    """Preview product, group-buying Njangi, or daily-summary content."""
    try:
        data = json.loads(request.body)
        draft_type = data.get("type")
        from . import prompts
        if draft_type == "business":
            from business.models import BusinessProfile
            obj = get_object_or_404(BusinessProfile.objects.filter(is_active=True), pk=data.get("object_id"))
            draft = prompts.generate_business_created_draft(obj)
        elif draft_type == "product":
            from business.models import BusinessCatalogItem
            obj = get_object_or_404(
                BusinessCatalogItem.objects.filter(is_active=True, business__is_active=True),
                pk=data.get("object_id"), item_type=BusinessCatalogItem.ItemType.PRODUCT,
            )
            draft = prompts.generate_product_draft(obj)
        elif draft_type == "njangi":
            from njangi.models import NjangiAchatGroupe
            obj = get_object_or_404(
                NjangiAchatGroupe.objects.filter(status=NjangiAchatGroupe.Status.OPEN)
                .select_related("product", "product__business"), pk=data.get("object_id")
            )
            draft = prompts.generate_njangi_draft(obj)
        elif draft_type == "daily_summary":
            draft = prompts.generate_daily_summary_draft()
        else:
            return JsonResponse({"status": "error", "message": "Type de brouillon inconnu."}, status=400)
        return JsonResponse({"status": "success", "type": draft_type, **draft})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@staff_required
@require_POST
def verify_meta_connection(request):
    """Explicitly verify the configured Page token and required permissions."""
    config = FacebookPageConfig.objects.filter(is_active=True).first()
    if not config:
        return JsonResponse({"status": "error", "message": "Aucune Page active configurée."}, status=409)
    from django.conf import settings
    from .facebook_api import FacebookAPIClient
    client = FacebookAPIClient(config.page_access_token, config.page_id, config.app_id, config.app_secret)
    result = client.verify_token()
    if not result.get("is_valid"):
        return JsonResponse({"status": "error", "message": result.get("error", "Jeton invalide ou expiré."),
                             "page_name": config.page_name, "page_id": config.page_id,
                             "token_valid": False}, status=400)
    scopes = set(result.get("scopes", []))
    required = {"pages_manage_posts", "pages_read_engagement", "pages_manage_engagement"}
    page_info = client.get_page_insights()
    page_matches = bool(page_info) and str(page_info.get("id", "")) == str(config.page_id)
    expected_app_id = config.app_id or getattr(settings, "FACEBOOK_APP_ID", "")
    app_matches = not expected_app_id or str(result.get("app_id", "")) == str(expected_app_id)
    missing = sorted(required - scopes)
    return JsonResponse({
        "status": "success" if page_matches and app_matches and not missing else "warning",
        "page_name": page_info.get("name", config.page_name), "page_id": config.page_id,
        "token_valid": True, "page_matches": page_matches, "app_matches": app_matches,
        "permissions": sorted(scopes), "missing_permissions": missing,
        "expires_at": result.get("expires_at"),
    })


@staff_required
@require_POST
def save_approved_draft(request):
    """Save an edited draft for human approval; this endpoint never publishes."""
    try:
        data = json.loads(request.body)
        content = (data.get("content") or "").strip()
        draft_type = data.get("type", "business")
        object_id = data.get("object_id")
        char_limit = 600 if draft_type == "daily_summary" else 300
        if not content or len(content) > char_limit:
            return JsonResponse({"status": "error", "message": f"Le texte doit contenir entre 1 et {char_limit} caractères."}, status=400)
        if len(re.findall(r"(?<!\w)#[\wÀ-ÿ]+", content)) > 3:
            return JsonResponse({"status": "error", "message": "Utilisez trois hashtags au maximum."}, status=400)

        from django.utils.dateparse import parse_datetime
        scheduled_at = parse_datetime(data.get("scheduled_at", ""))
        if not scheduled_at:
            return JsonResponse({"status": "error", "message": "Choisissez une date de publication."}, status=400)
        if timezone.is_naive(scheduled_at):
            scheduled_at = timezone.make_aware(scheduled_at)
        if scheduled_at < timezone.now():
            return JsonResponse({"status": "error", "message": "La date doit être dans le futur."}, status=400)

        from business.models import BusinessProfile, BusinessCatalogItem
        from njangi.models import NjangiAchatGroupe
        url = "https://e-shelle.com/"
        from .prompts import facebook_campaign_url
        section = "business"
        title = "Brouillon Facebook E-Shelle"
        if draft_type == "business":
            obj = get_object_or_404(BusinessProfile.objects.filter(is_active=True), pk=object_id)
            url = facebook_campaign_url(f"https://e-shelle.com/b/{obj.public_slug or obj.slug}/", f"business_{obj.pk}")
            title = f"Fiche business : {obj.name}"
        elif draft_type == "product":
            obj = get_object_or_404(BusinessCatalogItem.objects.filter(is_active=True, business__is_active=True), pk=object_id)
            url = facebook_campaign_url(f"https://e-shelle.com/b/{obj.business.public_slug or obj.business.slug}/", f"product_{obj.pk}")
            title = f"Produit : {obj.title}"
        elif draft_type == "njangi":
            obj = get_object_or_404(NjangiAchatGroupe.objects.select_related("product__business"), pk=object_id)
            url = facebook_campaign_url(f"https://e-shelle.com/b/{obj.product.business.public_slug or obj.product.business.slug}/", f"njangi_{obj.pk}")
            title = f"Njangi : {obj.product.title}"
            section = "njangi"
        elif draft_type != "daily_summary":
            return JsonResponse({"status": "error", "message": "Type de brouillon inconnu."}, status=400)

        if draft_type == "daily_summary":
            url = facebook_campaign_url(url, f"daily_{scheduled_at.date().isoformat()}")

        config = FacebookPageConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({"status": "error", "message": "Aucune Page Facebook active n'est configurée."}, status=409)
        from django.conf import settings
        max_daily = max(1, int(getattr(settings, "FACEBOOK_AGENT_MAX_POSTS_PER_DAY", 3)))
        from django.db.models import Q
        day_posts = ScheduledPost.objects.filter(scheduled_at__date=scheduled_at.date()).filter(
            Q(status__in=("en_attente", "approuve")) | Q(status="publie")
        ).count()
        day_posts += PublishedPost.objects.filter(published_at__date=scheduled_at.date()).exclude(
            scheduled_post__isnull=False
        ).count()
        if day_posts >= max_daily:
            return JsonResponse({"status": "error", "message": f"Le plafond de {max_daily} publications pour cette date est atteint."}, status=409)

        source_id = f"{draft_type}:{object_id or scheduled_at.date().isoformat()}"
        cooldown_days = 7 if draft_type == "product" else 1
        duplicate_cutoff = timezone.now() - timedelta(days=cooldown_days)
        if ScheduledPost.objects.filter(
            source_object_id=source_id,
            source_object_type="facebook_first_comment",
            created_at__gte=duplicate_cutoff,
        ).exclude(status="annule").exists():
            return JsonResponse({"status": "error", "message": "Un brouillon récent existe déjà pour cet élément."}, status=409)
        post = ScheduledPost.objects.create(
            page_config=config, section=section, title=title,
            content=content, link_url=url, scheduled_at=scheduled_at,
            status="en_attente", requires_approval=True, ai_generated=True,
            source_object_id=source_id,
            source_object_type="facebook_first_comment",
        )
        return JsonResponse({"status": "success", "message": "Brouillon enregistré en attente d'approbation.", "draft_id": str(post.id)})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)


@staff_required
@require_POST
def approve_scheduled_draft(request, scheduled_post_id):
    """Explicit staff approval schedules a draft for its selected publication time."""
    post = get_object_or_404(ScheduledPost, pk=scheduled_post_id)
    if post.status != "en_attente" or not post.requires_approval:
        messages.error(request, "Ce brouillon n'est plus en attente d'approbation.")
        return redirect("facebook_agent:scheduled_posts")
    if post.scheduled_at <= timezone.now():
        post.scheduled_at = timezone.now() + timedelta(minutes=5)
    post.status = "approuve"
    post.save(update_fields=["status", "scheduled_at", "updated_at"])
    messages.success(request, "Brouillon approuvé et programmé. Une date déjà passée est reportée de cinq minutes.")
    return redirect("facebook_agent:scheduled_posts")


# ------------------------------------------------------------------ #
# Logs de l'agent                                                     #
# ------------------------------------------------------------------ #

@staff_required
def agent_logs(request):
    """Liste des logs de l'agent."""
    from django.core.paginator import Paginator

    level_filter = request.GET.get("level", "")
    section_filter = request.GET.get("section", "")
    action_filter = request.GET.get("action", "")

    logs_qs = AgentLog.objects.order_by("-created_at")
    if level_filter:
        logs_qs = logs_qs.filter(level=level_filter)
    if section_filter:
        logs_qs = logs_qs.filter(section=section_filter)
    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)

    paginator = Paginator(logs_qs, 50)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "page_title": "Logs de l'Agent",
        "page_obj": page_obj,
        "level_filter": level_filter,
        "section_filter": section_filter,
        "action_filter": action_filter,
        "level_choices": AgentLog.LOG_LEVEL_CHOICES,
        "action_choices": AgentLog.ACTION_CHOICES,
        "section_choices": ContentRule.SECTION_CHOICES,
    }
    return render(request, "facebook_agent/logs.html", context)


# ------------------------------------------------------------------ #
# API: statut temps réel (polling AJAX)                               #
# ------------------------------------------------------------------ #

@staff_required
def api_status(request):
    """Retourne le statut actuel de l'agent en JSON."""
    from django.db.models import Sum

    today = timezone.now().date()
    config = FacebookPageConfig.objects.filter(is_active=True).first()

    data = {
        "page_active": config is not None,
        "page_name": config.page_name if config else None,
        "token_valid": None,
        "token_checked_by_meta": False,
        "published_today": PublishedPost.objects.filter(published_at__date=today).count(),
        "pending_posts": ScheduledPost.objects.filter(status__in=("en_attente", "approuve")).count(),
        "errors_today": AgentLog.objects.filter(created_at__date=today, level="error").count(),
        "last_post": None,
    }

    last_post = PublishedPost.objects.order_by("-published_at").first()
    if last_post:
        data["last_post"] = {
            "section": last_post.section,
            "published_at": last_post.published_at.isoformat(),
            "facebook_id": last_post.facebook_post_id,
        }

    return JsonResponse(data)
