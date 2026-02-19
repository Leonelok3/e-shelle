#!/usr/bin/env python3
"""
Générateur d'exams Expression Écrite (EE) A1-C2
Crée 195 questions d'examen répartis en 6 exams:
- A1: 20Q, A2: 25Q, B1: 30Q, B2: 35Q, C1: 40Q, C2: 45Q
"""

import json

EXAMS_AB = {
    "exams": [
        {
            "exam_code": "EE_A1_FR",
            "exam_name": "Examen A1 - Expression Écrite",
            "level": "A1",
            "section_code": "ee",
            "total_questions": 20,
            "time_limit_minutes": 30,
            "sections": [
                {
                    "section_code": "ee",
                    "section_name": "Expression Écrite - Niveau A1",
                    "instructions": "Écrivez des textes simples sur des sujets courants. Respectez le nombre de mots demandé.",
                    "questions": [
                        {
                            "question_number": i+1,
                            "stem": f"Question {i+1}: Écrivez {50+i*5} mots sur un sujet du quotidien (personnes, lieux, objets familiers)",
                            "section_code": "ee",
                            "question_type": "writing",
                            "context_info": f"Sujet {i+1}: Aspects basiques de communication écrite",
                            "expected_output": "Texte cohérent et compréhensible avec vocabulaire A1",
                        }
                        for i in range(20)
                    ]
                }
            ]
        },
        {
            "exam_code": "EE_A2_FR",
            "exam_name": "Examen A2 - Expression Écrite",
            "level": "A2",
            "section_code": "ee",
            "total_questions": 25,
            "time_limit_minutes": 40,
            "sections": [
                {
                    "section_code": "ee",
                    "section_name": "Expression Écrite - Niveau A2",
                    "instructions": "Écrivez des textes courts et connectés. Variez votre vocabulaire et vos structures.",
                    "questions": [
                        {
                            "question_number": i+1,
                            "stem": f"Question {i+1}: Écrivez {80+i*5} mots - communication écrite A2",
                            "section_code": "ee",
                            "question_type": "writing",
                            "context_info": f"Sujet {i+1}: Développement élémentaire",
                        }
                        for i in range(25)
                    ]
                }
            ]
        },
        {
            "exam_code": "EE_B1_FR",
            "exam_name": "Examen B1 - Expression Écrite",
            "level": "B1",
            "section_code": "ee",
            "total_questions": 30,
            "time_limit_minutes": 50,
            "sections": [
                {
                    "section_code": "ee",
                    "section_name": "Expression Écrite - Niveau B1",
                    "instructions": "Écrivez des textes développés avec argumentation. Organisez vos idées de façon claire.",
                    "questions": [
                        {
                            "question_number": i+1,
                            "stem": f"Question {i+1}: Écrivez {120+i*8} mots avec structure et argumentation",
                            "section_code": "ee",
                            "question_type": "writing",
                            "context_info": f"Sujet {i+1}: Expression et argumentation B1",
                        }
                        for i in range(30)
                    ]
                }
            ]
        },
        {
            "exam_code": "EE_B2_FR",
            "exam_name": "Examen B2 - Expression Écrite",
            "level": "B2",
            "section_code": "ee",
            "total_questions": 35,
            "time_limit_minutes": 60,
            "sections": [
                {
                    "section_code": "ee",
                    "section_name": "Expression Écrite - Niveau B2",
                    "instructions": "Écrivez des textes nuancés et persuasifs. Démontrez la maîtrise du français.",
                    "questions": [
                        {
                            "question_number": i+1,
                            "stem": f"Question {i+1}: Écrivez {180+i*10} mots avec nuance et persuasion",
                            "section_code": "ee",
                            "question_type": "writing",
                            "context_info": f"Sujet {i+1}: Maîtrise B2 - analyse et opinion",
                        }
                        for i in range(35)
                    ]
                }
            ]
        }
    ]
}

EXAMS_C = {
    "exams": [
        {
            "exam_code": "EE_C1_FR",
            "exam_name": "Examen C1 - Expression Écrite",
            "level": "C1",
            "section_code": "ee",
            "total_questions": 40,
            "time_limit_minutes": 75,
            "sections": [
                {
                    "section_code": "ee",
                    "section_name": "Expression Écrite - Niveau C1",
                    "instructions": "Écrivez des textes sophistiqués et élégants. Démontrez profondeur analytique.",
                    "questions": [
                        {
                            "question_number": i+1,
                            "stem": f"Question {i+1}: Écrivez {250+i*15} mots avec analyse sophiquée et style",
                            "section_code": "ee",
                            "question_type": "writing",
                            "context_info": f"Sujet {i+1}: Maîtrise C1 - pensée critique",
                        }
                        for i in range(40)
                    ]
                }
            ]
        },
        {
            "exam_code": "EE_C2_FR",
            "exam_name": "Examen C2 - Expression Écrite",
            "level": "C2",
            "section_code": "ee",
            "total_questions": 45,
            "time_limit_minutes": 90,
            "sections": [
                {
                    "section_code": "ee",
                    "section_name": "Expression Écrite - Niveau C2",
                    "instructions": "Écrivez avec maîtrise complète. Style littéraire, nuance et originalité attendus.",
                    "questions": [
                        {
                            "question_number": i+1,
                            "stem": f"Question {i+1}: Écrivez {350+i*20} mots avec excellence stylistique",
                            "section_code": "ee",
                            "question_type": "writing",
                            "context_info": f"Sujet {i+1}: Maîtrise C2 - excellence linguistique",
                        }
                        for i in range(45)
                    ]
                }
            ]
        }
    ]
}

def generate_exams():
    """Génère les fichiers exams"""
    
    # A1-B2
    print("[EXAMS] A1-B2...")
    ab_output_file = "ai_engine/learning_content/exams_writing_a_b_fr.json"
    with open(ab_output_file, "w", encoding="utf-8") as f:
        json.dump(EXAMS_AB, f, ensure_ascii=False, indent=2)
    total_ab = sum(e["total_questions"] for e in EXAMS_AB["exams"])
    print(f"  [OK] {ab_output_file} ({total_ab} questions)")
    
    # C1-C2
    print("[EXAMS] C1-C2...")
    c_output_file = "ai_engine/learning_content/exams_writing_c_fr.json"
    with open(c_output_file, "w", encoding="utf-8") as f:
        json.dump(EXAMS_C, f, ensure_ascii=False, indent=2)
    total_c = sum(e["total_questions"] for e in EXAMS_C["exams"])
    print(f"  [OK] {c_output_file} ({total_c} questions)")
    
    return total_ab + total_c

if __name__ == "__main__":
    print("[GENERATION] Exams Expression Écrite (EE) A1-C2")
    print("=" * 60)
    total = generate_exams()
    print("=" * 60)
    print(f"[SUCCESS] {total} EE questions created (6 exams: A1-C2)")
