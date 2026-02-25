#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour générer les exams de compréhension écrite (CE) A1-C2
Crée 2 fichiers JSON: exams_reading_<range>_fr.json
"""

import json
from pathlib import Path

def create_question(num, section_code="ce"):
    """Crée une question d'exam"""
    return {
        "question_number": num,
        "stem": f"Question {num}: Quel est le point principal du texte?",
        "passage_reference": 1 + (num % 3),
        "subtype": "mcq",
        "difficulty": "easy" if num <= 8 else ("medium" if num <= 15 else "hard"),
        "choices": [
            {"text": f"Réponse A pour question {num}", "is_correct": num % 4 == 0},
            {"text": f"Réponse B pour question {num}", "is_correct": num % 4 == 1},
            {"text": f"Réponse C pour question {num}", "is_correct": num % 4 == 2},
            {"text": f"Réponse D pour question {num}", "is_correct": num % 4 == 3}
        ],
        "explanation": f"Explication détaillée pour la question {num}."
    }

def create_passage(num):
    """Crée un passage de texte"""
    return {
        "passage_id": num,
        "title": f"Passage {num}: Article sur un sujet intéressant",
        "text": f"Ceci est un texte de compréhension écrite. Passage numéro {num}. " * 15  # ~150 mots
    }

def create_exam(code, name, level, num_questions=25):
    """Crée un examen complet"""
    return {
        "exam_code": code,
        "exam_name": name,
        "level": level,
        "language": "fr",
        "duration_sec": 900,
        "total_questions": num_questions,
        "description": f"Examen {code} - Compréhension écrite niveau {level}",
        "sections": [
            {
                "section_code": "ce",
                "section_name": "Compréhension Écrite",
                "order": 1,
                "duration_sec": 900,
                "passages": [create_passage(i) for i in range(1, 6)],
                "parts": [
                    {
                        "part_number": 1,
                        "part_title": "Lecture d'articles et textes courts",
                        "number_of_questions": num_questions,
                        "questions": [create_question(i, "ce") for i in range(1, num_questions + 1)]
                    }
                ]
            }
        ]
    }

# Fichier 1: A1-B2
exams_a_b = {
    "language": "fr",
    "exam_format": "DELF/DALF-inspired reading comprehension",
    "total_exams": 4,
    "exams": [
        create_exam("CE_A1_FR", "Examen A1 - Compréhension Écrite", "A1", 20),
        create_exam("CE_A2_FR", "Examen A2 - Compréhension Écrite", "A2", 25),
        create_exam("CE_B1_FR", "Examen B1 - Compréhension Écrite", "B1", 30),
        create_exam("CE_B2_FR", "Examen B2 - Compréhension Écrite", "B2", 35)
    ]
}

# Fichier 2: C1-C2
exams_c = {
    "language": "fr",
    "exam_format": "DALF reading comprehension",
    "total_exams": 2,
    "exams": [
        create_exam("CE_C1_FR", "Examen C1 - Compréhension Écrite", "C1", 40),
        create_exam("CE_C2_FR", "Examen C2 - Compréhension Écrite", "C2", 45)
    ]
}

output_dir = Path("ai_engine/learning_content")
output_dir.mkdir(parents=True, exist_ok=True)

# Générer fichiers
files = [
    (exams_a_b, "exams_reading_a_b_fr.json"),
    (exams_c, "exams_reading_c_fr.json")
]

for data, filename in files:
    filepath = output_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Created: {filepath}")

print(f"\n🎉 All 2 exam files generated! Total questions: {20+25+30+35+40+45} = 195 questions")
