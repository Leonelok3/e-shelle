from django import forms
from .models import PRProfile


class PREligibilityForm(forms.ModelForm):
    class Meta:
        model = PRProfile
        fields = [
            "country",
            "age",
            "years_experience",
            "education_level",

            "french_exam",
            "french_level",
            "french_co",
            "french_ce",
            "french_eo",
            "french_ee",

            "english_exam",
            "english_level",
            "english_co",
            "english_ce",
            "english_eo",
            "english_ee",

            "profession_title",
            "noc_code",
            "anzsco_code",
            "has_family_in_country",
            "has_job_offer",
            "notes",
        ]
        labels = {
            "country": "Pays ciblé",
            "age": "Âge",
            "years_experience": "Années d’expérience (temps plein)",
            "education_level": "Niveau d’études",

            "french_exam": "Test de français",
            "french_level": "Niveau global de français",
            "french_co": "Français – CO (compréhension orale)",
            "french_ce": "Français – CE (compréhension écrite)",
            "french_eo": "Français – EO (expression orale)",
            "french_ee": "Français – EE (expression écrite)",

            "english_exam": "Test d’anglais",
            "english_level": "Niveau global d’anglais",
            "english_co": "Anglais – Listening (CO)",
            "english_ce": "Anglais – Reading (CE)",
            "english_eo": "Anglais – Speaking (EO)",
            "english_ee": "Anglais – Writing (EE)",

            "profession_title": "Profession principale",
            "noc_code": "Code NOC / TEER (Canada)",
            "anzsco_code": "Code ANZSCO (Australie)",
            "has_family_in_country": "Famille sur place",
            "has_job_offer": "Offre d’emploi valide",
            "notes": "Infos complémentaires",
        }
