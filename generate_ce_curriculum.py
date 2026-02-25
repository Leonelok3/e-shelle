#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script pour générer le curriculum de compréhension écrite (CE) A1-C2
Crée 6 fichiers JSON: reading_curriculum_{LEVEL}_fr.json
"""

import json
import os
from pathlib import Path

# Configuration par niveau
CURRICULUM_CONFIG = {
    "A1": {
        "title": "Débutant absolu",
        "lessons": {
            1: ("Présentations simples", ["nom", "âge", "profession"], [
                "Salut! Je m'appelle Jean.",
                "Bonjour, je m'appelle Marie. J'ai 25 ans.",
                "Je suis pilote.",
                "Panneau: Ouvert de 9h à 17h.",
                "Ticket: Place n°12. Prix 5 euros."
            ]),
            2: ("Salutations et politesse", ["merci", "s'il vous plaît", "au revoir"], [
                "Merci beaucoup!",
                "S'il vous plaît, fermez la porte.",
                "Au revoir à bientôt!",
                "Excusez-moi, où est la gare?",
                "Bonjour, comment allez-vous?"
            ]),
            3: ("Nombres et horaires", ["heure", "prix", "numéro"], [
                "Bus arrive à 10h30.",
                "Menu: Café 2€, Sandwich 4€.",
                "Réunion mercredi à 14h.",
                "Tel: 06 12 34 56 78.",
                "Magasin: 9h-18h."
            ]),
            4: ("Famille et relations", ["mère", "père", "frère", "sœur"], [
                "Paul a une sœur. Elle s'appelle Emma.",
                "Bonjour maman, ça va?",
                "Mon père est cuisinier.",
                "Réunion famille dimanche.",
                "Je te présente ma sister."
            ]),
            5: ("Alimentation", ["pain", "eau", "fruits", "prix"], [
                "Sandwich 4€.",
                "Ingrédients: farine, sel, eau.",
                "Promotion: Chocolat -20%.",
                "Liste: lait, pain, oeufs.",
                "Réservation pour 2 personnes."
            ]),
            6: ("Vêtements et achats", ["robe", "pantalon", "shirt", "magasin"], [
                "Soldes jusqu'à 50%!",
                "T-shirt rouge: 15 euros.",
                "Ouverture boutique: 10h.",
                "Mode été 2026.",
                "Cabine essayage 2."
            ]),
            7: ("Logement", ["maison", "appartement", "chambre", "loyer"], [
                "Appartement 2 pièces à louer.",
                "Maison 3 chambres, 150 m².",
                "Loyer: 800 euros/mois.",
                "Proche métro.",
                "Garage inclus."
            ]),
            8: ("Transports", ["bus", "métro", "train", "voiture"], [
                "Ligne 5 métro: arrêt central.",
                "Train départ 10h00.",
                "Prochaine arrivée: 15 min.",
                "Parking gratuit dimanche.",
                "Bus n°12."
            ]),
            9: ("Santé et urgences", ["médecin", "pharmacie", "allergie"], [
                "Pharmacie 24h/24.",
                "Prendre un comprimé matin et soir.",
                "Reposez-vous.",
                "Sans gluten.",
                "RDV médecin jeudi 10h."
            ]),
            10: ("Lieux publics", ["gare", "école", "hôpital", "parc"], [
                "Gare SNCF centre-ville.",
                "Inscription école lundi.",
                "Hôpital ouvert 24h/24.",
                "Parc fermé 18h.",
                "Bibliothèque lundi-samedi."
            ]),
            11: ("Jours et dates", ["lundi", "janvier", "aujourd'hui", "demain"], [
                "Réunion lundi 10h.",
                "Ouvert 9h-18h (sauf dimanche).",
                "Cours mardi 18h.",
                "Fermé le 25 décembre.",
                "Événement samedi."
            ]),
            12: ("Activités quotidiennes", ["travailler", "dormir", "manger", "jouer"], [
                "Je travaille lundi-vendredi.",
                "Déjeuner 12h-14h.",
                "École 9h-17h.",
                "Match football samedi.",
                "Dîner 20h."
            ]),
            13: ("Météo et saisons", ["soleil", "pluie", "neige", "temperature"], [
                "Il y a du soleil aujourd'hui.",
                "Tempo max 25°C.",
                "Allons à la plage!",
                "Parapluie recommandé.",
                "Hiver 2026."
            ]),
            14: ("Descriptions simples", ["grand", "petit", "beau", "blanc"], [
                "La maison est grande.",
                "Chat noir et blanc.",
                "Voiture rouge.",
                "Ciel bleu.",
                "Fleur jaune."
            ]),
            15: ("Communications courtes", ["message", "urgent", "attendre", "merci"], [
                "Message: appel urgent.",
                "Veuillez patienter.",
                "Merci de rappeler.",
                "À bientôt.",
                "No entry."
            ])
        }
    },
    "A2": {
        "title": "Élémentaire",
        "lessons": {
            1: ("Messages courts", ["email", "rdv", "confirmation"], [
                "Je confirme notre rendez-vous demain à 15h.",
                "Vente samedi matin. Vêtements enfants.",
                "Rappel: vaccination jeudi 10h.",
                "Appartement à louer. Proche métro.",
                "Cours yoga mardi 18h."
            ]),
            2: ("Directions", ["gauche", "droite", "métro", "route"], [
                "Tournez à gauche puis droit.",
                "Prenez la ligne rouge.",
                "Station fermée dimanche.",
                "Parking central.",
                "Route nationale 1."
            ]),
            3: ("Horaires détaillés", ["ouverture", "fermeture", "horaire"], [
                "Métro: 5h30-0h30.",
                "Bibliothèque: lundi-samedi 9h-19h.",
                "Magasin fermé dimanche.",
                "Déjeuner 12h-14h.",
                "Service 24h/24."
            ]),
            4: ("Annonces immobilières", ["louer", "studio", "cuisine"], [
                "Studio 30m² à louer 600€.",
                "2 pièces, cuisine ouverte.",
                "Balcon, parking.",
                "Visite samedi.",
                "Proche écoles."
            ]),
            5: ("Invitations et événements", ["fête", "concert", "dîner"], [
                "Invitation: concert dimanche 20h.",
                "Entrée: 20 euros.",
                "Dîner famille samedi.",
                "Match football.",
                "Place assise."
            ]),
            6: ("Conseils et notes", ["conseil", "attention", "important"], [
                "Évitez aliments allergènes.",
                "Attention: travaux.",
                "Important: retards possibles.",
                "À bientôt.",
                "Rappel: vaccination."
            ]),
            7: ("Courtes histoires", ["jour", "matin", "soir", "nuit"], [
                "Hier, j'ai visité le parc.",
                "Nous avons pique-niqué.",
                "Dimanche matin, il y a du soleil.",
                "Allons à la plage!",
                "Le soir, on mange."
            ]),
            8: ("Itinéraires", ["nord", "sud", "est", "ouest"], [
                "Gare au nord.",
                "École centre-ville.",
                "Parc à l'est.",
                "Maison proche métro.",
                "Suivez la route."
            ]),
            9: ("Menus et restauration", ["menu", "plat", "boisson"], [
                "Aujourd'hui: soupe, poulet frites.",
                "Boissons: eau, soda, vin.",
                "Dessert: glace.",
                "Prix: menu 15€.",
                "Réservation obligatoire."
            ]),
            10: ("Billets et tickets", ["validité", "tarif", "classe"], [
                "Billet train Paris-Lyon.",
                "Départ 10h00.",
                "Arrivée 12h30.",
                "Place 12, voiture 3.",
                "Valable 48h."
            ]),
            11: ("Avis et notes", ["avis", "fermeture", "réouverture"], [
                "Fermeture exceptionnelle demain.",
                "Réouverture jeudi.",
                "Travaux en cours.",
                "Merci pour votre patience.",
                "À bientôt!"
            ]),
            12: ("Échange de messages", ["réponds", "question", "réponse"], [
                "Comment ça va?",
                "Ça va bien, et toi?",
                "Tu viens samedi?",
                "Oui, à 20h.",
                "À plus tard!"
            ]),
            13: ("Informations pratiques", ["info", "numéro", "adresse"], [
                "Tél: 01 23 45 67 89.",
                "Adresse: 10 rue du Centre.",
                "Email: info@example.com.",
                "Site: www.example.fr.",
                "Horaires sur demande."
            ]),
            14: ("Publicités simples", ["offre", "solde", "promo"], [
                "Grand solde jusqu'à 70%!",
                "2 pour 10 euros.",
                "Gratuit ce week-end.",
                "Livraison offerte.",
                "Stock limité!"
            ]),
            15: ("Conseils de santé", ["sommeil", "alimentation", "sport"], [
                "Dormez 8 heures.",
                "Mangez fruits et légumes.",
                "Faites du sport.",
                "Buvez 2 litres eau.",
                "Reposez-vous!"
            ])
        }
    },
    "B1": {
        "title": "Intermédiaire",
        "lessons": {
            i: (f"Leçon {i}: Thème variés", ["vocabulaire", "contexte"], [
                f"Texte exemple {i}.",
                f"Description contexte pour leçon {i}.",
                f"Question type {i}.",
                f"Passage illustratif {i}.",
                f"Contenu pédagogique {i}."
            ]) for i in range(1, 16)
        }
    },
    "B2": {
        "title": "Intermédiaire supérieur",
        "lessons": {
            i: (f"Leçon {i}: Sujets d'actualité", ["argument", "nuance"], [
                f"Article court topic {i}.",
                f"Information détaillée sujet {i}.",
                f"Analyse point {i}.",
                f"Contenu journalistique {i}.",
                f"Discussion professionnelle {i}."
            ]) for i in range(1, 16)
        }
    },
    "C1": {
        "title": "Avancé",
        "lessons": {
            i: (f"Leçon {i}: Textes complexes", ["critique", "subtilité"], [
                f"Essai analytique {i}.",
                f"Critique détaillée sujet {i}.",
                f"Argument nuancé {i}.",
                f"Perspective académique {i}.",
                f"Analyse profonde {i}."
            ]) for i in range(1, 16)
        }
    },
    "C2": {
        "title": "Maîtrise",
        "lessons": {
            i: (f"Leçon {i}: Pensée critique", ["implicite", "ironie"], [
                f"Essai philosophique {i}.",
                f"Critique littéraire nuancée {i}.",
                f"Interprétation subtile {i}.",
                f"Analyse herméneutique {i}.",
                f"Réflexion approfondie {i}."
            ]) for i in range(1, 16)
        }
    }
}

def create_exercise(exercise_num, passage_text, base_question, passage_title=""):
    """Crée un exercice simple"""
    exercise_type = "multiple_choice" if exercise_num % 2 == 1 else "vrai_faux"
    
    if exercise_type == "multiple_choice":
        return {
            "exercise_number": exercise_num,
            "type": "multiple_choice",
            "passage_title": passage_title or f"Passage {exercise_num}",
            "passage_text": passage_text,
            "question": base_question,
            "options": {
                "A": f"Option A pour question {exercise_num}",
                "B": f"Option B pour question {exercise_num}",
                "C": f"Option C pour question {exercise_num}",
                "D": f"Option D pour question {exercise_num}"
            },
            "correct_answer": ["A", "B", "C", "D"][exercise_num %4],
            "explanation": f"Explication pour l'exercice {exercise_num}.",
            "difficulty_progression": 1 + (exercise_num % 3)
        }
    else:
        return {
            "exercise_number": exercise_num,
            "type": "vrai_faux",
            "passage_title": passage_title or f"Passage {exercise_num}",
            "passage_text": passage_text,
            "question": base_question,
            "options": {},
            "correct_answer": "Vrai" if exercise_num % 2 == 0 else "Faux",
            "explanation": f"Explication pour l'exercice {exercise_num}.",
            "difficulty_progression": 1 + (exercise_num % 3)
        }

def generate_curriculum(level, config):
    """Génère un curriculum complet pour un niveau"""
    curriculum = {
        "level": level,
        "language": "fr",
        "total_lessons": 15,
        "exercises_per_lesson": 10,
        "cefr_standard": f"{level} - {config['title']}",
        "lessons": []
    }
    
    for lesson_num, (title, vocab, passages) in config['lessons'].items():
        lesson = {
            "lesson_number": lesson_num,
            "title": title,
            "slug": f"{level.lower()}-lecon-{lesson_num}-{title.lower().replace(' ', '-')}",
            "objective": f"Comprendre des textes de compréhension écrite niveau {level}",
            "vocabulary_focus": vocab,
            "exercises": []
        }
        
        # Créer 10 exercices par leçon
        for ex_num in range(1, 11):
            passage = passages[ex_num % len(passages)]
            exercise = create_exercise(
                ex_num,
                passage,
                f"Question {ex_num} sur le passage?",
                "Passage lecteur"
            )
            lesson["exercises"].append(exercise)
        
        curriculum["lessons"].append(lesson)
    
    return curriculum

# Générer tous les fichiers
output_dir = Path("ai_engine/learning_content")
output_dir.mkdir(parents=True, exist_ok=True)

for level in ["A1", "A2", "B1", "B2", "C1", "C2"]:
    if level in CURRICULUM_CONFIG:
        print(f"Generating {level} curriculum...")
        curriculum = generate_curriculum(level, CURRICULUM_CONFIG[level])
        
        filename = output_dir / f"reading_curriculum_{level}_fr.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(curriculum, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Created: {filename}")
    else:
        # Pour B1-C2, utiliser une génération par défaut
        print(f"Generating {level} curriculum (template)...")
        curriculum = {
            "level": level,
            "language": "fr",
            "total_lessons": 15,
            "exercises_per_lesson": 10,
            "cefr_standard": f"{level} - {CURRICULUM_CONFIG[level]['title']}",
            "lessons": [
                {
                    "lesson_number": i,
                    "title": f"Leçon {i}: Thèmes variés",
                    "slug": f"{level.lower()}-lecon-{i}",
                    "objective": f"Compréhension écrite niveau {level}",
                    "vocabulary_focus": ["vocabulaire", "contexte"],
                    "exercises": [
                        create_exercise(j, f"Passage de texte pour exercice {j}.", f"Question {j}?")
                        for j in range(1, 11)
                    ]
                }
                for i in range(1, 16)
            ]
        }
        
        filename = output_dir / f"reading_curriculum_{level}_fr.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(curriculum, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Created: {filename}")

print("\n🎉 All 6 curriculum files generated!")
