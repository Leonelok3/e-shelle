from django.test import TestCase
from django.contrib.auth import get_user_model

from ai_engine.agents import ContentAgentFactory


User = get_user_model()


class AIAgentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aiuser", password="x")

    def test_default_agent_generate_lesson(self):
        agent = ContentAgentFactory.get()
        res = agent.generate_lesson(level="A1", skill="co", topic="salutations")
        self.assertTrue(res.success)
        self.assertIn("title", res.data)
        self.assertIn("html", res.data)
