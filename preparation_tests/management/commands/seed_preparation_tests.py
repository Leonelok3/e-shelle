from django.core.management.base import BaseCommand
from django.db import transaction
from preparation_tests.models import Exam, ExamSection, Question, Choice, Explanation

class Command(BaseCommand):
    help = "Seed Préparation Tests (FR/EN/DE) : TCF, TEF, IELTS, GOETHE, TESTDAF, TELC — idempotent."

    @transaction.atomic
    def handle(self, *args, **options):
        # --- Examens à créer ---
        exams = [
            {"code": "tcf",     "name": "TCF",               "language": "fr"},
            {"code": "tef",     "name": "TEF",               "language": "fr"},
            {"code": "ielts",   "name": "IELTS",             "language": "en"},
            {"code": "goethe",  "name": "Goethe-Zertifikat", "language": "de"},
            {"code": "testdaf", "name": "TestDaF",           "language": "de"},
            {"code": "telc",    "name": "telc Deutsch",      "language": "de"},
        ]

        # --- Sauvegarde / mise à jour idempotente ---
        exam_objs = {}
        for e in exams:
            obj, _ = Exam.objects.get_or_create(
                code=e["code"],
                defaults={"name": e["name"], "language": e["language"]},
            )
            changed = False
            if obj.name != e["name"]:
                obj.name = e["name"]; changed = True
            if obj.language != e["language"]:
                obj.language = e["language"]; changed = True
            if changed:
                obj.save()
            exam_objs[e["code"]] = obj

        # --- Sections standard ---
        SECTIONS = [
            ("listening", 1, 600),
            ("reading",   2, 900),
            ("writing",   3, 1200),
            ("speaking",  4, 600),
        ]

        def ensure_sections(exam):
            out = {}
            for code, order, duration in SECTIONS:
                s, _ = ExamSection.objects.get_or_create(
                    exam=exam, code=code,
                    defaults={"order": order, "duration_sec": duration},
                )
                if s.order != order or s.duration_sec != duration:
                    s.order = order; s.duration_sec = duration; s.save()
                out[code] = s
            return out

        def mcq(section, stem, options, *, correct_index=0, difficulty=0.5, explanation=None):
            q, _ = Question.objects.get_or_create(
                section=section, stem=stem, subtype="mcq",
                defaults={"difficulty": difficulty},
            )
            if q.choices.count() == 0:
                for i, opt in enumerate(options):
                    Choice.objects.create(question=q, text=opt, is_correct=(i == correct_index))
                if explanation and not hasattr(q, "explanation"):
                    Explanation.objects.create(question=q, text_md=explanation)
            return q

        # === FR (TCF/TEF) ===
        tcf = exam_objs["tcf"]; tcf_sec = ensure_sections(tcf)
        mcq(tcf_sec["listening"],
            "Vous entendez: « Le train partira à 16h40. » Que signifie-t-on ?",
            ["Le train part à 14h40", "Le train part à 16h40", "Le train part à 18h40"],
            correct_index=1, explanation="On entend clairement **seize heures quarante**.")
        mcq(tcf_sec["reading"],
            "Choisissez le synonyme de « rapide ».",
            ["lent", "vite", "en retard"], correct_index=1)

        tef = exam_objs["tef"]; tef_sec = ensure_sections(tef)
        mcq(tef_sec["listening"],
            "Le conférencier parle surtout de :",
            ["son voyage", "son métier", "sa famille"], correct_index=1)
        mcq(tef_sec["reading"],
            "Dans le texte, « croissance » signifie :",
            ["augmentation", "diminution", "stagnation"], correct_index=0)

        # === EN (IELTS) ===
        ielts = exam_objs["ielts"]; ielts_sec = ensure_sections(ielts)
        mcq(ielts_sec["listening"],
            "The speaker mentions the meeting was moved to:",
            ["Monday morning", "Tuesday afternoon", "Friday evening"], correct_index=1)
        mcq(ielts_sec["reading"],
            "“beneficial” is closest in meaning to:",
            ["harmful", "useful", "neutral"], correct_index=1)

        # === DE (Goethe/TestDaF/telc) ===
        goethe = exam_objs["goethe"]; goethe_sec = ensure_sections(goethe)
        mcq(goethe_sec["reading"],
            "Wählen Sie das Synonym von „wichtig“:",
            ["bedeutend", "unnötig", "zufällig"], correct_index=0)
        mcq(goethe_sec["listening"],
            "Die Sprecherin sagt, dass der Termin auf ____ verschoben wurde.",
            ["Montagmorgen", "Dienstagnachmittag", "Freitagabend"], correct_index=2)

        testdaf = exam_objs["testdaf"]; testdaf_sec = ensure_sections(testdaf)
        mcq(testdaf_sec["reading"],
            "Im Text bedeutet „steigern“ am ehesten:",
            ["reduzieren", "erhöhen", "stabilisieren"], correct_index=1)
        mcq(testdaf_sec["listening"],
            "Worüber spricht der Dozent hauptsächlich?",
            ["Forschungsergebnisse", "Urlaubspläne", "Einladung zur Party"], correct_index=0)

        telc = exam_objs["telc"]; telc_sec = ensure_sections(telc)
        mcq(telc_sec["reading"],
            "Das Wort „geeignet“ ist am nächsten zu:",
            ["passend", "nutzlos", "schwierig"], correct_index=0)
        mcq(telc_sec["listening"],
            "Der Sprecher erwähnt, dass die Anmeldung bis ____ möglich ist.",
            ["heute", "morgen", "nächste Woche"], correct_index=2)

        self.stdout.write(self.style.SUCCESS("✅ Seed Préparation Tests — OK (FR/EN/DE)"))
