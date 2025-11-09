from typing import List, Dict

def explain_with_citations(program_code: str, country: str) -> Dict:
    """
    Placeholder RAG : ici tu appelleras ton moteur (BM25+vector).
    Retourne toujours des citations (url, titre, date).
    """
    return {
        "citations": [
            {"title": "IRCC official page", "url": "https://www.canada.ca/en/immigration-refugees-citizenship.html"},
            {"title": "Campus France", "url": "https://www.campusfrance.org/fr"},
        ],
        "summary": f"Les critères officiels pour {program_code} ({country}) proviennent des sites gouvernementaux listés."
    }
