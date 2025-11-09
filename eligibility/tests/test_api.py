# eligibility/tests/test_api.py
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from eligibility.models import Program, ProgramCriterion

class EligibilityFlowTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="ana@example.com", password="pwd")
        self.client = Client()
        self.client.login(username="ana@example.com", password="pwd")

        p = Program.objects.create(
            code="can_study", title="Canada Study", country="Canada",
            category="study", url_official="https://example.com",
            min_score=50, active=True
        )
        ProgramCriterion.objects.create(program=p, key="age", op="gte", value_json=17, weight=1, required=True)
        ProgramCriterion.objects.create(program=p, key="language.ielts.overall", op="gte", value_json=6.0, weight=2, required=False)

    def test_scoring_flow(self):
        # create session
        res = self.client.post("/api/eligibility/sessions/", {"locale": "fr"})
        self.assertEqual(res.status_code, 201)
        sid = res.json()["id"]

        # answers
        r = self.client.post(f"/api/eligibility/sessions/{sid}/answers/", content_type="application/json",
                             data='{"age":18,"language.ielts.overall":6.5}')
        self.assertEqual(r.status_code, 200)

        # score
        r2 = self.client.post(f"/api/eligibility/sessions/{sid}/score/?country=Canada")
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertTrue(data["results"][0]["eligible"])
