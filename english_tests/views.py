from django.shortcuts import render

def english_hub(request):
    """
    Hub principal pour les tests d'anglais (IELTS, TOEFL, TOEIC).
    Pour l’instant, vitrine + navigation. Plus tard : cours, entraînements, stats.
    """
    exams = [
        {
            "code": "ielts",
            "slug": "ielts",
            "label": "IELTS",
            "level": "B1 – C2",
            "goals": "Études à l’étranger, immigration, travail.",
        },
        {
            "code": "toefl",
            "slug": "toefl",
            "label": "TOEFL iBT",
            "level": "B1 – C2",
            "goals": "Universités anglophones, programmes d’échange.",
        },
        {
            "code": "toeic",
            "slug": "toeic",
            "label": "TOEIC",
            "level": "A2 – C1",
            "goals": "Anglais professionnel, carrière en entreprise.",
        },
    ]
    return render(
        request,
        "english_tests/english_hub.html",
        {"exams": exams},
    )


def ielts_hub(request):
    """
    Sous-hub IELTS : plus tard tu mettras les cours, entraînements, examens blancs.
    """
    return render(
        request,
        "english_tests/ielts_hub.html",
        {},
    )


def toefl_hub(request):
    """
    Sous-hub TOEFL.
    """
    return render(
        request,
        "english_tests/toefl_hub.html",
        {},
    )


def toeic_hub(request):
    """
    Sous-hub TOEIC.
    """
    return render(
        request,
        "english_tests/toeic_hub.html",
        {},
    )



from django.shortcuts import render

def exam_list(request):
    return render(request, "english_tests/exam_list.html")
