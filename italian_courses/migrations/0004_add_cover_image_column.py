from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("italian_courses", "0003_alter_lesson_cover_image"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE italian_courses_lesson
            ADD COLUMN IF NOT EXISTS cover_image varchar(100);
            """,
            reverse_sql="""
            ALTER TABLE italian_courses_lesson
            DROP COLUMN IF EXISTS cover_image;
            """,
        )
    ]
