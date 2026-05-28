from io import BytesIO

from django.utils import timezone

from .models import BusinessLeadEvent


def business_report_context(business, days: int = 30):
    since = timezone.now() - timezone.timedelta(days=days)
    events = business.lead_events.filter(created_at__gte=since)
    views = events.filter(event_type=BusinessLeadEvent.EventType.VIEW).count()
    contacts = events.filter(
        event_type__in=[
            BusinessLeadEvent.EventType.WHATSAPP,
            BusinessLeadEvent.EventType.PHONE,
            BusinessLeadEvent.EventType.ORDER,
        ]
    ).count()
    details = events.filter(event_type=BusinessLeadEvent.EventType.DETAIL).count()
    total = events.count()
    event_stats = list(events.values("event_type").order_by("event_type"))
    summary = (
        f"Rapport E-Shelle {days} jours pour {business.name}: "
        f"{views} vues IA/home, {contacts} contacts, {details} clics detail, "
        f"plan actuel: {business.get_plan_display()}."
    )
    return {
        "events": events,
        "views": views,
        "contacts": contacts,
        "details": details,
        "total": total,
        "summary": summary,
        "days": days,
    }


def render_business_report_pdf(business, context: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.6 * cm,
        leftMargin=1.6 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        title=f"Rapport E-Shelle - {business.name}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "EShelleTitle",
        parent=styles["Title"],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#111827"),
        spaceAfter=12,
    )
    section_style = ParagraphStyle(
        "EShelleSection",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#16A34A"),
        spaceBefore=14,
        spaceAfter=8,
    )
    normal = styles["BodyText"]

    story = [
        Paragraph("Rapport de performance E-Shelle", title_style),
        Paragraph(f"<b>{business.name}</b> - {business.get_module_display()} - {business.city or 'Ville non renseignee'}", normal),
        Paragraph(f"Periode analysee : {context['days']} jours", normal),
        Spacer(1, 0.35 * cm),
    ]

    metrics = [
        ["Vues", "Contacts", "Details", "Total actions"],
        [context["views"], context["contacts"], context["details"], context["total"]],
    ]
    metrics_table = Table(metrics, colWidths=[4 * cm, 4 * cm, 4 * cm, 4 * cm])
    metrics_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#ECFDF5")),
                ("TEXTCOLOR", (0, 1), (-1, 1), colors.HexColor("#111827")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 18),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.extend([metrics_table, Spacer(1, 0.4 * cm)])

    story.append(Paragraph("Resume partageable", section_style))
    story.append(Paragraph(context["summary"], normal))

    recent_events = context["events"].order_by("-created_at")[:20]
    story.append(Paragraph("Derniers evenements", section_style))
    rows = [["Date", "Action", "Source"]]
    rows.extend(
        [
            [event.created_at.strftime("%d/%m/%Y %H:%M"), event.get_event_type_display(), event.source]
            for event in recent_events
        ]
    )
    if len(rows) == 1:
        rows.append(["-", "Aucun evenement sur la periode", "-"])
    table = Table(rows, colWidths=[4.4 * cm, 5.2 * cm, 5.8 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16A34A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                ("PADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    return buffer.getvalue()
