from django.core.management.base import BaseCommand
from django.test.utils import override_settings


class Command(BaseCommand):
    help = 'Vérifie les générateurs locaux sans paiement ni écriture en base.'

    def add_arguments(self, parser):
        parser.add_argument('--reset-cooldown', action='store_true', help='Autoriser immédiatement une nouvelle tentative IA après recharge.')

    def handle(self, *args, **options):
        from ai_engine.services.availability import reset
        from ai_engine.services.llm_service import call_llm
        from ai_engine.services.local_content import resume_documents
        from ai_engine.services.learning_fallback import lesson
        if options['reset_cooldown']:
            reset()
        with override_settings(AI_CONTENT_MODE='offline'):
            assert call_llm('test', 'test', fallback='local') == 'local'
            for language in ('fr', 'en', 'de', 'bilingual'):
                html, letter = resume_documents('Nom : Test', '', language)
                assert html and letter
            for language in ('fr', 'de'):
                for level in ('A1', 'A2', 'B1', 'B2', 'C1', 'C2'):
                    assert lesson(language, level, 'LESEN' if language == 'de' else 'ce')['exercises']
        self.stdout.write(self.style.SUCCESS('Générateurs locaux OK. Aucun appel IA payant, aucune écriture en base.'))
