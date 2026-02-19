import os
import tempfile
import shutil

from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model

from preparation_tests.models import (
    Exam,
    CourseLesson,
    CEFRCertificate,
)

from preparation_tests.services.level_engine import try_unlock_next_level
from preparation_tests.services.recommendations import recommend_lessons
from preparation_tests.services.study_plan import build_study_plan


User = get_user_model()


class ServicesSmokeTests(TestCase):
    def setUp(self):
        # media dir pour la génération de certificats
        self.tmp_media = tempfile.mkdtemp(prefix="imm97_test_media_")
        self.override = override_settings(MEDIA_ROOT=self.tmp_media)
        self.override.enable()

        self.user = User.objects.create_user(username="tester", password="pass")

        self.exam = Exam.objects.create(code="TEF", name="TEF Exam", language="fr")

    def tearDown(self):
        try:
            self.override.disable()
        finally:
            shutil.rmtree(self.tmp_media, ignore_errors=True)

    def test_try_unlock_next_level_unlocks_and_creates_certificate(self):
        # score below threshold -> no unlock
        res = try_unlock_next_level(user=self.user, exam_code="TEF", skill="co", score_percent=60)
        self.assertFalse(res.get("unlocked"))

        # score above threshold -> unlock
        res2 = try_unlock_next_level(user=self.user, exam_code="TEF", skill="co", score_percent=75)
        self.assertTrue(res2.get("unlocked"))

        # certificat créé for the new level
        certs = CEFRCertificate.objects.filter(user=self.user, exam_code__iexact="TEF")
        self.assertTrue(certs.exists())

    def test_recommend_lessons_returns_relevant_lessons(self):
        # crée une leçon liée à l'examen
        lesson = CourseLesson.objects.create(
            title="Leçon 1",
            slug="lecon-1",
            section="co",
            level="A1",
            content_html="<p>Test</p>",
            is_published=True,
        )
        lesson.exams.add(self.exam)

        per_section = {"CO": {"pct": 50}}

        recs = recommend_lessons(user=self.user, exam_code="TEF", per_section=per_section)

        self.assertTrue(len(recs) >= 1)
        self.assertEqual(recs[0]["lesson"].slug, lesson.slug)

    def test_build_study_plan_returns_days(self):
        # crée plusieurs leçons A1 pour l'examen
        for i in range(3):
            l = CourseLesson.objects.create(
                title=f"L{i}",
                slug=f"l{i}",
                section="co",
                level="A1",
                content_html="x",
                is_published=True,
            )
            l.exams.add(self.exam)

        plan = build_study_plan(user=self.user, exam_code="TEF")

        self.assertIsInstance(plan, dict)
        self.assertIn("days", plan)
        self.assertGreaterEqual(len(plan["days"]), 1)
