from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .services import (
    CTAAgent,
    ContentSEOAgent,
    GoogleBusinessAgent,
    LocalSEOAgent,
    SEOCorrectionAgent,
    SEOAuditAgent,
    SchemaAgent,
    build_sitemap_entries,
)


def staff_required(view_func):
    return staff_member_required(view_func, login_url="/accounts/login/")


@staff_required
def dashboard(request):
    audit = SEOAuditAgent().run()
    local_agent = LocalSEOAgent()
    geo_ideas = local_agent.ideas()
    geo_priorities = local_agent.prioritized_pages(request=request)
    return render(
        request,
        "seo_agent/dashboard.html",
        {
            "audit": audit,
            "geo_ideas": geo_ideas[:18],
            "geo_priorities": geo_priorities,
            "geo_total": len(geo_ideas),
            "schema_suggestions": SchemaAgent().suggestions(),
            "cta_suggestions": CTAAgent().suggestions(),
            "content_briefs": ContentSEOAgent().briefs(),
            "gbp_drafts": GoogleBusinessAgent().drafts(),
            "sitemap_entries": build_sitemap_entries(request),
        },
    )


@staff_required
def correction_plan(request):
    file_path = request.GET.get("file", "")
    issue = request.GET.get("issue", "")
    try:
        plan = SEOCorrectionAgent().plan_for(file_path, issue)
        error = ""
    except Exception as exc:
        plan = None
        error = str(exc)
    return render(request, "seo_agent/correction_plan.html", {"plan": plan, "error": error})


def article_index(request):
    return render(request, "seo_agent/article_index.html")


def article_marche_numerique(request):
    return render(
        request,
        "seo_agent/article_marche_numerique.html",
        {
            "published_at": timezone.datetime(2026, 5, 31),
        },
    )


def robots_txt(request):
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /accounts/",
        "Disallow: /dashboard/",
        "Disallow: /whatsapp/",
        "Disallow: /commercial-agent/",
        "Disallow: /phone-ocr/",
        f"Sitemap: {request.scheme}://{request.get_host()}/sitemap.xml",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain; charset=utf-8")


def sitemap_xml(request):
    entries = build_sitemap_entries(request)
    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')
    today = timezone.localdate().isoformat()
    for entry in entries:
        xml.append("  <url>")
        xml.append(f"    <loc>{entry['loc']}</loc>")
        xml.append(f"    <lastmod>{today}</lastmod>")
        xml.append("    <changefreq>weekly</changefreq>")
        xml.append("    <priority>0.8</priority>")
        xml.append("  </url>")
    xml.append("</urlset>")
    return HttpResponse("\n".join(xml), content_type="application/xml; charset=utf-8")
