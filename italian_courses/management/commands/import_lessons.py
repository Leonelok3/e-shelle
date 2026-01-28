import json
from django.core.management.base import BaseCommand, CommandError
from italian_courses.models import CourseCategory, Lesson, Quiz, Question, Choice
from italian_courses.sanitizer import sanitize_html

class Command(BaseCommand):
    help = "Import categories/lessons (+ optional quizzes) from a JSON file."

    def add_arguments(self, parser):
        parser.add_argument("json_path", type=str, help="Path to JSON file.")

    def handle(self, *args, **options):
        path = options["json_path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise CommandError(f"Cannot read JSON: {e}")

        categories = data.get("categories", [])
        lessons = data.get("lessons", [])

        cat_map = {}
        for c in categories:
            obj, _ = CourseCategory.objects.get_or_create(
                slug=c["slug"], defaults={"name": c.get("name", c["slug"])}
            )
            if obj.name != c.get("name", obj.name):
                obj.name = c.get("name", obj.name)
                obj.save()
            cat_map[obj.slug] = obj

        created = updated = 0
        for l in lessons:
            cat_slug = l["category_slug"]
            if cat_slug not in cat_map:
                raise CommandError(f"Unknown category_slug: {cat_slug}")

            cleaned = sanitize_html(l.get("content_html", ""))

            obj, is_created = Lesson.objects.update_or_create(
                slug=l.get("slug") or None,
                defaults={
                    "category": cat_map[cat_slug],
                    "title": l["title"],
                    "excerpt": l.get("excerpt", ""),
                    "level": l.get("level", "A0"),
                    "order_index": int(l.get("order_index", 1)),
                    "content_html": cleaned,
                    "is_published": bool(l.get("is_published", False)),
                },
            )
            if is_created:
                created += 1
            else:
                updated += 1

            # Optional quiz import
            quiz_data = l.get("quiz")
            if quiz_data:
                quiz, _ = Quiz.objects.update_or_create(
                    lesson=obj,
                    defaults={"title": quiz_data.get("title", "Quiz"), "is_active": bool(quiz_data.get("is_active", True))}
                )
                # Reset questions/choices for idempotent import
                quiz.questions.all().delete()
                for qi, qd in enumerate(quiz_data.get("questions", []), start=1):
                    q = Question.objects.create(quiz=quiz, prompt=qd["prompt"], order_index=qd.get("order_index", qi))
                    for cd in qd.get("choices", []):
                        Choice.objects.create(question=q, text=cd["text"], is_correct=bool(cd.get("is_correct", False)))

        self.stdout.write(self.style.SUCCESS(f"Import finished. Created={created}, Updated={updated}"))
