import json
from ai_engine.prompts.co_prompt import CO_SYSTEM_PROMPT
from ai_engine.services.llm_service import call_llm
from ai_engine.validators.co_validator import validate_co_json

def generate_co_content(language, level):
    response = call_llm(
        system_prompt=CO_SYSTEM_PROMPT,
        user_prompt=f"Génère une leçon CO niveau {level} en {language}"
    )

    data = json.loads(response)
    validate_co_json(data)
    return data
