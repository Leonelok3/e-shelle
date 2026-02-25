import json

from ai_engine.agents.co_agent import generate_co_content
from ai_engine.agents.ce_agent import generate_ce_content
from ai_engine.agents.eo_agent import generate_eo_content
from ai_engine.agents.ee_agent import generate_ee_content


class _LegacyResult(dict):
    def __getattr__(self, item):
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc


def _ensure_dict(raw):
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"raw": parsed}
        except Exception:
            return {"raw": raw}
    return {"raw": raw}


def _build_html(data: dict, skill: str) -> str:
    parts = []
    if data.get("title"):
        parts.append(f"<h2>{data['title']}</h2>")
    if data.get("topic"):
        parts.append(f"<h3>{data['topic']}</h3>")
    if data.get("reading_text"):
        parts.append(f"<p>{data['reading_text']}</p>")
    if data.get("audio_script"):
        parts.append(f"<p>{data['audio_script']}</p>")
    if data.get("instructions"):
        parts.append(f"<p>{data['instructions']}</p>")
    if data.get("sample_answer"):
        parts.append(f"<p>{data['sample_answer']}</p>")

    if not parts:
        parts.append(f"<p>Contenu généré ({skill}).</p>")

    return "\n".join(parts)


def _to_legacy_result(raw, skill: str):
    data = _ensure_dict(raw)

    if "title" not in data:
        data["title"] = data.get("topic") or f"Leçon {skill}"

    # Compat test legacy: assertIn("html", res.data)
    if "html" not in data or not data.get("html"):
        data["html"] = _build_html(data, skill)

    return _LegacyResult({"success": True, "data": data})


class _AgentAdapter:
    def __init__(self, generator, skill: str):
        self._generator = generator
        self._skill = skill

    def generate_content(self, language: str = "fr", level: str = "A1"):
        return self._generator(language=language, level=level)

    def generate(self, language: str = "fr", level: str = "A1"):
        return self._generator(language=language, level=level)

    def generate_lesson(self, language: str = "fr", level: str = "A1", **kwargs):
        raw = self._generator(language=language, level=level)
        return _to_legacy_result(raw, self._skill)


class ContentAgentFactory:
    _MAP = {
        "CO": generate_co_content,
        "CE": generate_ce_content,
        "EO": generate_eo_content,
        "EE": generate_ee_content,
    }

    @classmethod
    def create(cls, skill: str):
        key = (skill or "").strip().upper()
        if key not in cls._MAP:
            raise ValueError("Unsupported skill. Allowed: CO, CE, EO, EE.")
        return _AgentAdapter(cls._MAP[key], key)

    @classmethod
    def get_agent(cls, skill: str):
        return cls.create(skill)

    @classmethod
    def get(cls, skill: str = "CE"):
        return cls.create(skill)


__all__ = [
    "generate_co_content",
    "generate_ce_content",
    "generate_eo_content",
    "generate_ee_content",
    "ContentAgentFactory",
]