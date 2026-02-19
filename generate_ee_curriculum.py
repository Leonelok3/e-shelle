#!/usr/bin/env python3
"""
Générateur de curriculum Expression Écrite (EE) A1-C2
Crée 900 exercices d'écriture (150 par niveau, 10 par leçon, 15 leçons par niveau)
"""

import json
import os

# Configuration par niveau
LEVELS_CONFIG = {
    "A1": {
        "file": "ai_engine/learning_content/writing_curriculum_A1_fr.json",
        "lessons": [
            ("Présentations écrites", "Écrire des phrases simples sur soi-même", 
             ["vocabulaire de base", "pronoms simples", "verbe être/avoir"]),
            ("Messages courts", "Rédiger des messages simples", 
             ["ponctuation de base", "phrases affirmatives", "questions simples"]),
            ("Listes et énumérations", "Créer des listes organisées",
             ["organiser les idées", "énumération", "structure simple"]),
            ("Descriptions élémentaires", "Décrire des personnes ou objets",
             ["adjectifs courants", "ordre des mots", "accord basique"]),
            ("Formulaires simples", "Remplir des formulaires de base",
             ["informations personnelles", "structure de formulaire", "clarté"]),
            ("Invitations écrites", "Écrire une invitation simple",
             ["formules d'invitation", "détails essentiels", "ton approprié"]),
            ("Remerciements écrits", "Écrire un message de remerciement",
             ["formules de politesse", "structure", "authenticité"]),
            ("Notes et rappels", "Écrire des notes courtes",
             ["concision", "clarté", "organisation"]),
            ("Dialogues écrits", "Créer des échanges dialogues",
             ["ponctuation dialogues", "prononciation écrite", "ton naturel"]),
            ("Cartes postales", "Rédiger une carte postale",
             ["format typique", "contenu essentiel", "ton amical"]),
            ("Horaires et dates", "Noter des informations temporelles",
             ["formats de date", "clarté temporelle", "utilité"]),
            ("Adresses et directions", "Noter des adresses/directions",
             ["précision", "structure", "clarté géographique"]),
            ("Menus simples", "Créer un menu basique",
             ["vocabulaire culinaire", "organisation", "clarté"]),
            ("Annonces brèves", "Rédiger une annonce courte",
             ["accroche", "informations clés", "appel à action"]),
            ("Histoires très courtes", "Écrire une mini-histoire",
             ["début-milieu-fin", "temps de base", "logique narrative"]),
        ]
    },
    "A2": {
        "file": "ai_engine/learning_content/writing_curriculum_A2_fr.json",
        "lessons": [
            ("Courriers informels", "Écrire une lettre amicale",
             ["structure informelle", "ton personnel", "détails pertinents"]),
            ("Avis et opinions", "Exprimer son avis par écrit",
             ["verbes d'opinion", "justification simple", "structure"]),
            ("Instructions élémentaires", "Rédiger des instructions simples",
             ["ordre logique", "clarté imperative", "précision"]),
            ("Recettes simples", "Écrire une recette de base",
             ["ingrédients", "étapes", "format typique"]),
            ("Blog posts élémentaires", "Écrire un petit article blog",
             ["introduction", "développement", "conclusion"]),
            ("Critiques courtes", "Écrire un avis/critique simple",
             ["description", "opinion", "recommandation"]),
            ("Messages d'urgence", "Rédiger un message urgent",
             ["clarté", "priorité", "concision"]),
            ("Excuses écrites", "Écrire un message d'excuse",
             ["reconnaissance", "justification", "réparation"]),
            ("Rendez-vous écrits", "Proposer/confirmer un rendez-vous",
             ["clarté temporelle", "formalité adaptée", "confirmation"]),
            ("Demandes polies", "Formuler une demande par écrit",
             ["politesse", "raison", "ton approprié"]),
            ("Descriptions détaillées", "Décrire lieu ou personnes",
             ["adjectifs variés", "ordre logique", "cohérence"]),
            ("Comparaisons écrites", "Comparer par écrit",
             ["structures comparatives", "logique", "clarté"]),
            ("Résumés courts", "Résumer un texte simplement",
             ["idées principales", "concision", "fidélité"]),
            ("Expériences personnelles", "Raconter une expérience",
             ["passé composé", "logique narrative", "détails"]),
            ("Échanges de messages", "Correspondance par texte",
             ["ton informel", "réactivité", "pertinence"]),
        ]
    },
    "B1": {
        "file": "ai_engine/learning_content/writing_curriculum_B1_fr.json",
        "lessons": [
            ("Lettres formelles", "Rédiger une lettre professionnelle",
             ["structure formelle", "registre soutenu", "courtoisie"]),
            ("Essais et arguments", "Écrire un essai argumentatif",
             ["thèse", "arguments", "conclusion"]),
            ("Email professionnel", "Écrire un email de travail",
             ["clarté professionnelle", "politesse", "efficacité"]),
            ("Résumés et synthèses", "Synthétiser des informations",
             ["idées principales", "logique", "concision"]),
            ("Articles informatifs", "Rédiger un article factuel",
             ["structure", "objectivité", "clarté"]),
            ("Critiques approfondies", "Évaluer œuvre/produit",
             ["analyse", "justification", "style"]),
            ("Autobiographie simple", "Écrire sur sa vie",
             ["chronologie", "pertinence", "personnalité"]),
            ("Narration complexe", "Raconter une histoire détaillée",
             ["structure narrative", "description", "dialogue"]),
            ("Instructions détaillées", "Rédiger des instructions claires",
             ["étapes logiques", "précision", "complétude"]),
            ("Plans et projets", "Planifier par écrit",
             ["structure organisée", "détails", "réalisme"]),
            ("Débats écrits", "Argumenter pour/contre",
             ["anti-thèse", "contre-arguments", "nuance"]),
            ("Rapports simples", "Écrire un court rapport",
             ["objectivité", "structure", "faits"]),
            ("Recommandations", "Recommander quelque chose",
             ["justification", "persuasion", "détails"]),
            ("Descriptions atmosphériques", "Créer une ambiance",
             ["adjectifs évocateurs", "sensorialité", "style"]),
            ("Échanges réflexifs", "Correspondance réfléchie",
             ["profondeur", "sincérité", "nuance"]),
        ]
    },
    "B2": {
        "file": "ai_engine/learning_content/writing_curriculum_B2_fr.json",
        "lessons": [
            ("Essais développés", "Rédiger un véritable essai",
             ["thèse élaborée", "arguments multiples", "nuance"]),
            ("Correspondance formelle", "Lettres administratives",
             ["protocole", "registre élevé", "efficacité"]),
            ("Analyse critique", "Analyser texte/œuvre",
             ["structure analytique", "citations", "interprétation"]),
            ("Mémoires et récits", "Raconter des souvenirs",
             ["introspection", "détails significatifs", "réflexion"]),
            ("Propositions écrites", "Proposer un projet",
             ["clarté de vision", "justification", "faisabilité"]),
            ("Publications en ligne", "Rédiger un post réfléchi",
             ["engagement", "style adapté", "impact"]),
            ("Études de cas", "Analyser un cas spécifique",
             ["contexte", "analyse", "implications"]),
            ("Débats approfondis", "Argumenter sophistiqué",
             ["dialectique", "contre-exemples", "synthèse"]),
            ("Préfaces et introductions", "Introduire un sujet",
             ["accroche", "contexte", "enjeux"]),
            ("Correspondance nuancée", "Lettres émotionnelles",
             ["sincérité élégante", "tact", "émotion mesurée"]),
            ("Fiches de lecture", "Analyser un texte lu",
             ["résumé", "critique", "réflexion"]),
            ("Manifestes et déclarations", "Écrire avec conviction",
             ["passion contenue", "clarté", "persuasion"]),
            ("Analyses comparatives", "Comparer deux textes",
             ["structure compare", "nuance", "finesse"]),
            ("Reportages écrits", "Rédiger un reportage",
             ["enquête", "témoignages", "objectivité narrative"]),
            ("Essais de style personnel", "Écrire authentiquement",
             ["voix propre", "originalité", "profondeur"]),
        ]
    },
    "C1": {
        "file": "ai_engine/learning_content/writing_curriculum_C1_fr.json",
        "lessons": [
            ("Dissertations complexes", "Rédiger une dissertation",
             ["problématique", "démonstration", "dépassement antithèse"]),
            ("Critique littéraire", "Analyser une œuvre littéraire",
             ["lexique spécialisé", "interprétation", "justification textuelle"]),
            ("Correspondance diplomatique", "Lettres délicates",
             ["diplomatie", "implicite", "tact sophistiqué"]),
            ("Articles académiques", "Écrire un article de recherche",
             ["rigueur", "sources", "argumentation académique"]),
            ("Préfaces critiques", "Écrire une préface",
             ["contextualisation", "enjeux", "appel à lecture"]),
            ("Analyses socio-politiques", "Analyser société/politique",
             ["complexité", "nuance", "implicites culturels"]),
            ("Autobiographies réflexives", "Mémoires analytiques",
             ["introspection sophistiquée", "distance temporelle", "psychologie"]),
            ("Fictions narratives", "Écrire un récit créatif",
             ["style littéraire", "univers cohérent", "émotions nuancées"]),
            ("Traités et essais", "Essai philosophique/éthique",
             ["pensée personnelle", "références", "cohérence idéologique"]),
            ("Correspondance intime", "Lettres personnelles profondes",
             ["authenticité profonde", "vulnérabilité élégante", "poésie prose"]),
            ("Critiques artistiques", "Évaluer une création artistique",
             ["vocabulaire esthétique", "interprétation sensible", "jugement"]),
            ("Analyses historiques", "Étudier époque/événement",
             ["contextualisation historique", "causalité", "implications"]),
            ("Essais thématiques", "Explorer un thème profondément",
             ["amplitude", "finesse", "originalité intellectuelle"]),
            ("Pièces théâtrales courtes", "Écrire du dialogue dramatique",
             ["caractérisation", "tension dramatique", "didascalies"]),
            ("Essais scientifiques", "Vulgariser science/idée",
             ["rigueur", "clarté conceptuelle", "accessibilité"]),
        ]
    },
    "C2": {
        "file": "ai_engine/learning_content/writing_curriculum_C2_fr.json",
        "lessons": [
            ("Dissertations magistrales", "Dissertation expertise",
             ["pensée critique avancée", "structures argumentatives", "dépassement catégories"]),
            ("Herméneutique textuelle", "Interpréter profondément",
             ["lecture critique", "implicites", "jeu intertextuel"]),
            ("Correspondance raffinée", "Lettres nuancées", 
             ["subtilité", "ironie élégante", "sophistication"]),
            ("Monographies académiques", "Petit traité sur sujet",
             ["recherche originale", "synthèse", "contribution"]),
            ("Postfaces et épigraphes", "Clore une œuvre",
             ["récapitulation élégante", "ouverture", "résonance finale"]),
            ("Analyses médias et culture", "Critique culturelle",
             ["sémiologie", "contexte sociétal", "déconstruction"]),
            ("Autobiographies poétiques", "Mémoires littéraires",
             ["prose poétique", "temporalité complexe", "symbolisme"]),
            ("Créations narratives", "Roman ou novela courte",
             ["construction narrative", "polymécanismes", "style personnel"]),
            ("Traités philosophiques", "Pensée personnelle déployée",
             ["système de pensée", "cohérence", "originalité philosophique"]),
            ("Lettres d'amour intellectuelles", "Correspondance existentielle",
             ["profondeur", "poésie", "engagement personnel"]),
            ("Critiques psychanalytiques", "Analyse profonde d'œuvre",
             ["vocabulaire psychanalytique", "interprétation inconsciente", "pertinence"]),
            ("Histoires philosophiques", "Récit illustrant idée",
             ["parabole", "allégorie", "message implicite"]),
            ("Essais métacritiques", "Écrire sur l'écriture",
             ["autoréflexion", "style comme sujet", "réflexivité"]),
            ("Dialogues platoniciens", "Dialogue philosophique",
             ["tension dialectique", "caractérisation", "progrès idéologique"]),
            ("Manifestes poétiques", "Déclaration artistique",
             ["poétique personnelle", "audace", "beauté de l'énoncé"]),
        ]
    }
}

def generate_exercise(level, lesson_num, exercise_num, objective_keywords):
    """Génère un exercice individuel"""
    return {
        "lesson_number": lesson_num,
        "exercise_number": exercise_num,
        "objective": f"Exercice {exercise_num}: Développer l'expression écrite sur le thème",
        "prompt": f"Écrivez un texte (ou plusieurs phrases) abordant l'aspect suivant: {', '.join(objective_keywords[:2])}",
        "word_count_min": 50 + (lesson_num * 20),
        "word_count_max": 150 + (lesson_num * 30),
        "context": f"Contexte: Cette leçon {lesson_num} du niveau {level} vous demande de pratiquer l'écriture avec focus sur: {', '.join(objective_keywords)}",
        "example_answer": f"Exemple: Un texte de {100 + exercise_num * 10} mots montrant les éléments clés...",
        "evaluation_criteria": {
            "grammar_accuracy": "Grammaire correcte et appropriée",
            "vocabulary_range": f"Vocabulaire varié et niveau {level}",
            "organization": "Texte bien organisé et logique",
            "clarity": "Message clair et compréhensible",
            "style": "Style adapté au contexte et au niveau"
        },
        "difficulty_level": f"Niveau {level}",
        "common_mistakes": f"Éviter: erreurs de conjugaison, structure confuse, répétitions inutiles"
    }

def generate_lesson(level_code, lesson_num, lesson_title, lesson_objective, keywords):
    """Génère une leçon avec 10 exercices"""
    exercises = []
    for ex_num in range(1, 11):
        exercises.append({
            "exercise": generate_exercise(level_code, lesson_num, ex_num, keywords)
        })
    
    return {
        "lesson_number": lesson_num,
        "title": lesson_title,
        "slug": f"{level_code.lower()}-writing-lesson-{lesson_num}",
        "objective": lesson_objective,
        "vocabulary_focus": keywords,
        "exercises": exercises
    }

def generate_curriculum():
    """Génère tous les fichiers curriculum pour tous les niveaux"""
    for level_code, config in LEVELS_CONFIG.items():
        print(f"\n[CURRICULUM] {level_code}...")
        
        lessons = []
        for lesson_idx, (title, objective, keywords) in enumerate(config["lessons"], 1):
            lesson = generate_lesson(level_code, lesson_idx, title, objective, keywords)
            lessons.append(lesson)
            print(f"  [OK] Lesson {lesson_idx}: {title} ({len(lesson['exercises'])} exercises)")
        
        # Sauvegarder le fichier
        output = {
            "level": level_code,
            "section": "ee",
            "locale": "fr",
            "lessons": lessons
        }
        
        with open(config["file"], "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        
        total_exercises = len(lessons) * 10
        print(f"[SAVED] {config['file']} ({total_exercises} exercises)")

if __name__ == "__main__":
    print("[GENERATION] Curriculum Expression Écrite (EE) A1-C2")
    print("=" * 60)
    generate_curriculum()
    print("\n" + "=" * 60)
    print("[SUCCESS] Generation complete! 900 EE exercises created")
