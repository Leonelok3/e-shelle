from __future__ import annotations

try:
    from rest_framework import serializers  # type: ignore
except Exception:  # pragma: no cover
    serializers = None

from italian_courses.models import CourseCategory, Lesson, Quiz, Question, Choice

if serializers:
    class CourseCategorySerializer(serializers.ModelSerializer):
        class Meta:
            model = CourseCategory
            fields = ["id", "name", "slug"]

    class LessonSerializer(serializers.ModelSerializer):
        category = CourseCategorySerializer()

        class Meta:
            model = Lesson
            fields = [
                "id", "title", "slug", "excerpt", "level", "order_index",
                "is_published", "category", "cover_image", "content_html",
            ]

    class ChoiceSerializer(serializers.ModelSerializer):
        class Meta:
            model = Choice
            fields = ["id", "text"]

    class QuestionSerializer(serializers.ModelSerializer):
        choices = ChoiceSerializer(many=True)

        class Meta:
            model = Question
            fields = ["id", "prompt", "order_index", "choices"]

    class QuizSerializer(serializers.ModelSerializer):
        questions = QuestionSerializer(many=True)

        class Meta:
            model = Quiz
            fields = ["id", "title", "is_active", "questions"]
