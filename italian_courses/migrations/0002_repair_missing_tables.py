from django.conf import settings
from django.db import migrations


def forwards(apps, schema_editor):
    conn = schema_editor.connection
    existing = set(conn.introspection.table_names())

    app_label, model_name = settings.AUTH_USER_MODEL.split(".")
    User = apps.get_model(app_label, model_name)
    user_table = User._meta.db_table

    with conn.cursor() as c:

        # QUIZ
        if "italian_courses_quiz" not in existing:
            c.execute("""
                CREATE TABLE italian_courses_quiz (
                    id BIGSERIAL PRIMARY KEY,
                    lesson_id BIGINT UNIQUE NOT NULL
                        REFERENCES italian_courses_lesson(id)
                        DEFERRABLE INITIALLY DEFERRED,
                    title varchar(200) NOT NULL,
                    is_active boolean NOT NULL DEFAULT true
                );
            """)

        # QUESTION
        if "italian_courses_question" not in existing:
            c.execute("""
                CREATE TABLE italian_courses_question (
                    id BIGSERIAL PRIMARY KEY,
                    quiz_id BIGINT NOT NULL
                        REFERENCES italian_courses_quiz(id)
                        DEFERRABLE INITIALLY DEFERRED,
                    prompt text NOT NULL,
                    order_index integer NOT NULL DEFAULT 1
                );
            """)
            c.execute("""
                CREATE INDEX italian_courses_question_quiz_id_idx
                ON italian_courses_question(quiz_id);
            """)

        # CHOICE
        if "italian_courses_choice" not in existing:
            c.execute("""
                CREATE TABLE italian_courses_choice (
                    id BIGSERIAL PRIMARY KEY,
                    question_id BIGINT NOT NULL
                        REFERENCES italian_courses_question(id)
                        DEFERRABLE INITIALLY DEFERRED,
                    text varchar(300) NOT NULL,
                    is_correct boolean NOT NULL DEFAULT false
                );
            """)
            c.execute("""
                CREATE INDEX italian_courses_choice_question_id_idx
                ON italian_courses_choice(question_id);
            """)

        # LESSON PROGRESS
        if "italian_courses_lessonprogress" not in existing:
            c.execute(f"""
                CREATE TABLE italian_courses_lessonprogress (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL
                        REFERENCES {user_table}(id)
                        DEFERRABLE INITIALLY DEFERRED,
                    lesson_id BIGINT NOT NULL
                        REFERENCES italian_courses_lesson(id)
                        DEFERRABLE INITIALLY DEFERRED,
                    is_completed boolean NOT NULL DEFAULT false,
                    completed_at timestamptz NULL,
                    updated_at timestamptz NOT NULL DEFAULT NOW(),
                    CONSTRAINT italian_courses_lessonprogress_unique
                        UNIQUE (user_id, lesson_id)
                );
            """)
            c.execute("""
                CREATE INDEX italian_courses_lessonprogress_user_id_idx
                ON italian_courses_lessonprogress(user_id);
            """)
            c.execute("""
                CREATE INDEX italian_courses_lessonprogress_lesson_id_idx
                ON italian_courses_lessonprogress(lesson_id);
            """)


def backwards(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("italian_courses", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
