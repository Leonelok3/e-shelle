from datetime import date, timedelta
from typing import Iterable
from django.utils import timezone
from ..models import Source, Opportunity
import re

def score_opportunity(o: Opportunity) -> int:
    score = 50
    if o.deadline:
        days = (o.deadline - date.today()).days
        if 0 <= days <= 60:
            score += 20
    if o.is_scholarship:
        score += 10
    if o.category in ("work","pr"):
        score += 5
    return max(0, min(score, 100))

def upsert_opportunity(data: dict, source: Source) -> Opportunity:
    temp = Opportunity(
        title=data["title"],
        country=data["country"],
        category=data["category"],
        is_scholarship=data.get("is_scholarship", False),
        url=data["url"],
        deadline=data.get("deadline"),
        cost_min=data.get("cost_min"),
        cost_max=data.get("cost_max"),
        currency=data.get("currency", "USD"),
        eligibility_tags=data.get("eligibility_tags", []),
        source=source,
    )
    h = temp.compute_hash()
    obj, created = Opportunity.objects.update_or_create(
        hash=h,
        defaults={
            "title": temp.title,
            "country": temp.country,
            "category": temp.category,
            "is_scholarship": temp.is_scholarship,
            "url": temp.url,
            "deadline": temp.deadline,
            "cost_min": temp.cost_min,
            "cost_max": temp.cost_max,
            "currency": temp.currency,
            "eligibility_tags": temp.eligibility_tags,
            "score": score_opportunity(temp),
            "source": source,
        },
    )
    return obj

def sample_feed_for(source_code: str) -> Iterable[dict]:
    # MVP : faux flux utiles pour démo (tu pourras remplacer par scrape/API)
    today = date.today()
    if source_code == "IRCC":
        return [
            {
                "title": "Canada – Bourse partielle maîtrise IA",
                "country": "Canada",
                "category": "scholarship",
                "is_scholarship": True,
                "url": "https://www.canada.ca/scholarships",
                "deadline": today + timedelta(days=30),
                "eligibility_tags": ["Licence","IELTS>=6"],
            },
            {
                "title": "Canada – Employeurs désignés (Global Talent)",
                "country": "Canada",
                "category": "work",
                "url": "https://www.canada.ca/global-talent",
                "deadline": None,
                "eligibility_tags": ["Tech","Exp>=1"],
            },
        ]
    if source_code == "CAMPUSFR":
        return [
            {
                "title": "France – Bourses excellence licence/master",
                "country": "France",
                "category": "scholarship",
                "is_scholarship": True,
                "url": "https://www.campusfrance.org/fr/bourses",
                "deadline": today + timedelta(days=45),
                "eligibility_tags": ["Secondaire","Licence"],
            }
        ]
    if source_code == "DAAD":
        return [
            {
                "title": "Allemagne – DAAD scholarship (Master)",
                "country": "Allemagne",
                "category": "scholarship",
                "is_scholarship": True,
                "url": "https://www.daad.de/en/",
                "deadline": today + timedelta(days=25),
                "eligibility_tags": ["Licence","Allemand A2+"],
            }
        ]
    if source_code == "UKVI":
        return [
            {
                "title": "UK – Skilled Worker (sponsors list mise à jour)",
                "country": "Royaume-Uni",
                "category": "work",
                "url": "https://www.gov.uk/government/collections/register-of-licensed-sponsors-workers",
                "deadline": None,
                "eligibility_tags": ["IELTS>=5.5","Exp>=1"],
            }
        ]
    if source_code == "US_EDU":
        return [
            {
                "title": "USA – F-1 : universités à faible coût",
                "country": "USA",
                "category": "study",
                "url": "https://educationusa.state.gov/",
                "deadline": None,
                "eligibility_tags": ["TOEFL>=60","Budget>=15000"],
            }
        ]
    return []

def run_source(source: Source) -> int:
    count = 0
    for item in sample_feed_for(source.code):
        upsert_opportunity(item, source)
        count += 1
    source.last_run_at = timezone.now()
    source.save(update_fields=["last_run_at"])
    return count
