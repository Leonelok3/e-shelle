from django.shortcuts import render


SEO_PAGES = {
    "cameroun": {
        "title": "Rencontre serieuse au Cameroun",
        "h1": "Rencontre serieuse au Cameroun",
        "city": "Cameroun",
        "intro": (
            "E-Shelle Love aide les Camerounais et la diaspora a faire des rencontres plus "
            "serieuses, avec profils verifies, photos validees et messagerie encadree."
        ),
        "points": [
            "Profils camerounais verifies manuellement.",
            "Rencontres pour relations serieuses, pas seulement du swipe.",
            "Paiement Mobile Money avec activation manuelle.",
        ],
    },
    "douala": {
        "title": "Rencontre serieuse a Douala",
        "h1": "Rencontre serieuse a Douala",
        "city": "Douala",
        "intro": (
            "Trouvez des profils compatibles a Douala : entrepreneurs, professionnels, "
            "et personnes qui veulent construire une relation claire."
        ),
        "points": [
            "Decouverte de profils proches de Douala.",
            "Photos approuvees avant publication.",
            "Coach Love pour aider a envoyer un premier message respectueux.",
        ],
    },
    "yaounde": {
        "title": "Rencontre serieuse a Yaounde",
        "h1": "Rencontre serieuse a Yaounde",
        "city": "Yaounde",
        "intro": (
            "E-Shelle Love accompagne les rencontres serieuses a Yaounde avec matching, "
            "profils detailles, signalement et moderation."
        ),
        "points": [
            "Profils compatibles selon age, valeurs, langues et centres d'interet.",
            "Messagerie apres match.",
            "Options premium simples : 3 jours, 10 jours ou 1 mois.",
        ],
    },
}


def seo_landing(request, slug):
    page = SEO_PAGES.get(slug)
    if not page:
        from django.http import Http404
        raise Http404
    return render(request, "rencontres/seo_landing.html", {"page": page, "slug": slug})
