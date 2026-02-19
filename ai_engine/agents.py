"""
Scaffold for AI content creation agents.

Each agent produces instructional content for a given CEFR level and skill.
This is minimal scaffold — adapt to your production AI infra (OpenAI / Google etc.).
"""
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class AgentResult:
    success: bool
    data: Dict[str, Any]


class BaseContentAgent:
    """Base agent interface for content generation."""

    def __init__(self, model: str | None = None):
        self.model = model or "default"

    def generate_lesson(self, level: str, skill: str, topic: str) -> AgentResult:
        """Return a dict with lesson content (title, html, exercises).

        This implementation is a local deterministic stub for tests.
        Override this method to call external LLMs.
        """
        title = f"{level} — {skill} — {topic} (exemple)"
        html = f"<h1>{title}</h1><p>Contenu pédagogique généré pour {level}.</p>"
        exercises = [
            {"question": "Que veut dire ...?", "choices": ["A", "B", "C"], "answer": "A"}
        ]

        return AgentResult(success=True, data={"title": title, "html": html, "exercises": exercises})


class ContentAgentFactory:
    _registry: Dict[str, BaseContentAgent] = {}

    @classmethod
    def register(cls, name: str, agent: BaseContentAgent):
        cls._registry[name] = agent

    @classmethod
    def get(cls, name: str | None = None) -> BaseContentAgent:
        if not name:
            name = "default"
        return cls._registry.get(name, BaseContentAgent())


# Register a default agent
ContentAgentFactory.register("default", BaseContentAgent())
