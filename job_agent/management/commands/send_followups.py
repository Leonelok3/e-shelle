from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from job_agent.models import JobLead, FollowUpTemplate, CandidateProfile
from job_agent.services import render_text_template, send_followup_email


class Command(BaseCommand):
    help = "Envoie automatiquement les relances (7 jours après candidature) pour les leads postulés."

    def handle(self, *args, **options):
        now = timezone.now()
        cutoff = now - timedelta(days=7)

        qs = (
            JobLead.objects.filter(
                status=JobLead.STATUS_APPLIED,
                applied_at__isnull=False,
                applied_at__lte=cutoff,
                followup_sent_at__isnull=True,
            )
            .exclude(contact_email="")
            .exclude(contact_email__isnull=True)
        )

        sent = 0
        for lead in qs.select_related("user", "search"):
            profile, _ = CandidateProfile.objects.get_or_create(user=lead.user)
            language = (lead.search.language if lead.search else (profile.language or "fr")).lower()

            tpl = (
                FollowUpTemplate.objects.filter(is_active=True, language=language)
                .order_by("-id")
                .first()
            )

            name = profile.full_name or lead.user.get_username()
            title = lead.title or (lead.search.title if lead.search else "Poste")
            company = lead.company or ""
            location = lead.location or ""

            if tpl:
                subject = render_text_template(tpl.subject, name=name, title=title, company=company, location=location)
                body = render_text_template(tpl.content, name=name, title=title, company=company, location=location)
            else:
                subject = f"Relance — {title} ({company})"
                body = (
                    "Bonjour,\n\n"
                    f"Je me permets de relancer ma candidature au poste {title}"
                    f"{(' à ' + location) if location else ''}.\n"
                    "Je reste disponible pour un échange (entretien / test).\n\n"
                    f"Cordialement,\n{name}\n"
                )

            subject = (subject or "").strip()
            body = (body or "").strip()
            if not subject or not body:
                self.stdout.write(self.style.WARNING(f"[SKIP] Template vide pour lead={lead.id}"))
                continue

            try:
                send_followup_email(to_email=lead.contact_email, subject=subject, body=body)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[ERROR] lead={lead.id} SMTP: {e}"))
                continue

            lead.followup_sent_at = now
            lead.status = JobLead.STATUS_FOLLOWUP
            lead.save(update_fields=["followup_sent_at", "status"])

            sent += 1

        self.stdout.write(self.style.SUCCESS(f"Relances envoyées : {sent}"))
