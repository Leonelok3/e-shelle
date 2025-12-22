LEVEL_CHOICES = [
    ("A1", "A1"),
    ("A2", "A2"),
    ("B1", "B1"),
    ("B2", "B2"),
    ("C1", "C1"),
    ("C2", "C2"),
]

LEVEL_ORDER = {
    "A1": 1,
    "A2": 2,
    "B1": 3,
    "B2": 4,
    "C1": 5,
    "C2": 6,
}

LEVEL_PASS_THRESHOLD = {
    "A1": 60,
    "A2": 65,
    "B1": 70,
    "B2": 75,
    "C1": 80,
}



# ======================
# CECRL BADGES
# ======================

CEFR_BADGES = {
    "A1": {
        "label": "Débutant",
        "color": "#64748b",
        "icon": "🌱",
    },
    "A2": {
        "label": "Élémentaire",
        "color": "#0ea5e9",
        "icon": "📘",
    },
    "B1": {
        "label": "Indépendant",
        "color": "#22c55e",
        "icon": "🚀",
    },
    "B2": {
        "label": "Avancé",
        "color": "#16a34a",
        "icon": "🔥",
    },
    "C1": {
        "label": "Autonome",
        "color": "#f59e0b",
        "icon": "🏆",
    },
    "C2": {
        "label": "Maîtrise",
        "color": "#7c3aed",
        "icon": "👑",
    },
}
