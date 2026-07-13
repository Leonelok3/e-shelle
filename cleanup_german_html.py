import html
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "edu_cm.settings")
django.setup()

from GermanPrepApp.models import GermanLesson, GermanExercise, GermanPlacementQuestion

print("Unescaping Lessons...")
for l in GermanLesson.objects.all():
    l.title = html.unescape(l.title)
    l.intro = html.unescape(l.intro)
    l.content = html.unescape(l.content)
    l.save()

print("Unescaping Exercises...")
for e in GermanExercise.objects.all():
    e.question_text = html.unescape(e.question_text)
    e.option_a = html.unescape(e.option_a)
    e.option_b = html.unescape(e.option_b)
    e.option_c = html.unescape(e.option_c)
    e.option_d = html.unescape(e.option_d)
    e.explanation = html.unescape(e.explanation)
    e.save()

print("Unescaping Placement Questions...")
for q in GermanPlacementQuestion.objects.all():
    q.question_text = html.unescape(q.question_text)
    q.option_a = html.unescape(q.option_a)
    q.option_b = html.unescape(q.option_b)
    q.option_c = html.unescape(q.option_c)
    q.option_d = html.unescape(q.option_d)
    q.save()

print("CLEANUP_SUCCESSFUL")
