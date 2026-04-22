"""
python manage.py create_test_candidates
Crée 2 candidats de test pour valider generate_employer_targets.
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crée 2 profils candidats de test (agriculteur Canada + menuisier France)."

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from profiles.models import Profile, Category, Skill, ProfileSkill
        from job_agent.models import CandidateProfile

        User = get_user_model()

        cat_agri, _ = Category.objects.get_or_create(name="Agriculture", defaults={"slug": "agriculture"})
        cat_const, _ = Category.objects.get_or_create(name="Construction", defaults={"slug": "construction"})

        # ── Candidat 1 : Ouvrier agricole → Canada ──
        u1, created1 = User.objects.get_or_create(
            username="candidat_test1",
            defaults={"email": "amadou.diallo.test@gmail.com", "first_name": "Amadou", "last_name": "Diallo"},
        )
        if created1:
            u1.set_password("Test1234!")
            u1.save()

        CandidateProfile.objects.get_or_create(user=u1, defaults={
            "full_name": "Amadou Diallo",
            "country": "Sénégal",
            "city": "Dakar",
            "preferred_location": "Canada",
            "preferred_contract": "CDI",
        })

        p1, _ = Profile.objects.get_or_create(user=u1, defaults={
            "category": cat_agri,
            "headline": "Ouvrier agricole | 5 ans expérience maraîchage",
            "bio": "Travailleur agricole expérimenté, maraîchage et élevage. Cherche opportunité au Canada.",
            "level": "B1",
            "location": "Dakar, Sénégal",
            "is_public": True,
        })
        for name, lvl, yrs in [("Maraîchage", 4, 5), ("Irrigation", 3, 3), ("Conduite engins agricoles", 3, 2), ("Élevage", 3, 4)]:
            sk, _ = Skill.objects.get_or_create(name=name)
            ProfileSkill.objects.get_or_create(profile=p1, skill=sk, defaults={"level": lvl, "years": yrs})

        # ── Candidat 2 : Menuisier → France ──
        u2, created2 = User.objects.get_or_create(
            username="candidat_test2",
            defaults={"email": "kofi.mensah.test@gmail.com", "first_name": "Kofi", "last_name": "Mensah"},
        )
        if created2:
            u2.set_password("Test1234!")
            u2.save()

        CandidateProfile.objects.get_or_create(user=u2, defaults={
            "full_name": "Kofi Mensah",
            "country": "Côte d'Ivoire",
            "city": "Abidjan",
            "preferred_location": "France",
            "preferred_contract": "CDI",
        })

        p2, _ = Profile.objects.get_or_create(user=u2, defaults={
            "category": cat_const,
            "headline": "Menuisier | Charpentier qualifié | 7 ans expérience",
            "bio": "Menuisier charpentier avec solide expérience. Cherche poste en France.",
            "level": "B2",
            "location": "Abidjan, Côte d'Ivoire",
            "is_public": True,
        })
        for name, lvl, yrs in [("Menuiserie", 5, 7), ("Charpente", 4, 5), ("Coffrage", 3, 4), ("Lecture de plans", 4, 6)]:
            sk, _ = Skill.objects.get_or_create(name=name)
            ProfileSkill.objects.get_or_create(profile=p2, skill=sk, defaults={"level": lvl, "years": yrs})

        self.stdout.write(self.style.SUCCESS(
            f"✅ candidat_test1 — {p1.category.name} → {u1.candidate_profile.preferred_location} | public={p1.is_public}"
        ))
        self.stdout.write(self.style.SUCCESS(
            f"✅ candidat_test2 — {p2.category.name} → {u2.candidate_profile.preferred_location} | public={p2.is_public}"
        ))
        self.stdout.write("\nLance maintenant :")
        self.stdout.write("  python manage.py generate_employer_targets --dry-run")
