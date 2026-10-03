from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from pathlib import Path

from .forms import TemplateSelectionForm
from .meta_templates import approved_templates, TemplateError
from .models import Campagne, MessageEnvoi
from .tasks import _traiter_message_direct, envoyer_message_task


TEMPLATE = {'key': 'intro|fr', 'name': 'intro', 'language': 'fr', 'category': 'MARKETING',
    'body': 'Bonjour {{1}}', 'parameter_count': 1, 'supported': True, 'reason': ''}


@override_settings(WHATSAPP_WABA_ID='456', WHATSAPP_BUSINESS_ID='')
class CatalogTests(TestCase):
    def setUp(self):
        cache.clear()

    @patch('whatsapp_agent.meta_templates.requests.get')
    def test_matching_phone_paginated_catalog_and_status(self, get):
        def response(payload):
            from unittest.mock import Mock
            return Mock(status_code=200, json=lambda: payload)
        get.side_effect = [response({'data': [{'id': '123'}]}),
            response({'data': [{'name': 'intro', 'language': 'fr', 'status': 'APPROVED',
                'components': [{'type': 'BODY', 'text': 'Bonjour {{1}}'}]}],
                'paging': {'next': 'https://irrelevant', 'cursors': {'after': 'abc'}}}),
            response({'data': [{'name': 'pending', 'language': 'fr', 'status': 'PENDING'},
                {'name': 'photo', 'language': 'fr', 'status': 'APPROVED',
                'components': [{'type': 'HEADER', 'format': 'IMAGE'}]}]})]
        templates = approved_templates()
        self.assertEqual([t['name'] for t in templates], ['intro', 'photo'])
        self.assertEqual(templates[0]['parameter_count'], 1)
        self.assertFalse(templates[1]['supported'])
        self.assertEqual(get.call_args.kwargs['params']['after'], 'abc')

    @patch('whatsapp_agent.meta_templates._pages', return_value=[{'id': '999'}])
    def test_wrong_account_is_rejected(self, pages):
        with self.assertRaises(TemplateError):
            approved_templates()
        self.assertEqual(pages.call_count, 1)


class TemplateCampaignTests(TestCase):
    @override_settings(TEMPLATES=[{
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [Path(__file__).resolve().parent.parent / 'templates'],
        'OPTIONS': {'loaders': [
            ('django.template.loaders.locmem.Loader', {
                'base.html': '{% block content %}{% endblock %}',
                'partials/whatsapp_nav.html': '',
            }),
            'django.template.loaders.filesystem.Loader',
            'django.template.loaders.app_directories.Loader',
        ]},
    }])
    def test_detail_and_creation_render_selector_and_saved_preview(self):
        self.configure()
        response = self.client.get(reverse('whatsapp_agent:wa_detail', args=[self.campaign.pk]))
        self.assertContains(response, 'name="meta_template"')
        self.assertContains(response, 'Bonjour Leonel')
        self.assertContains(response, 'data-selected="intro|fr"')
        response = self.client.get(reverse('whatsapp_agent:wa_creer'))
        self.assertContains(response, 'meta_selector.js')

    def setUp(self):
        self.user = get_user_model().objects.create_user(username='template-staff', is_staff=True)
        self.client.force_login(self.user)
        self.campaign = Campagne.objects.create(nom='Template', message_template='Texte',
            filtre_role='selection_contacts', statut='validee')
        self.message = MessageEnvoi.objects.create(campagne=self.campaign, destinataire_nom='Leonel Dupont',
            numero_whatsapp='+237699000001', message_final='Texte original')

    @patch('whatsapp_agent.meta_templates.approved_templates', return_value=[TEMPLATE])
    def test_select_existing_campaign_and_reject_invalid_parameters(self, catalog):
        url = reverse('whatsapp_agent:wa_modele', args=[self.campaign.pk])
        self.client.post(url, {'meta_template': 'intro|fr', 'meta_params': '["{{prenom}}"]'})
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.template_meta_name, 'intro')
        self.assertEqual(self.campaign.template_meta_language, 'fr')
        self.message.refresh_from_db()
        self.assertEqual(self.message.message_final, 'Texte original')
        form = TemplateSelectionForm({'meta_template': 'intro|fr', 'meta_params': '[]'})
        self.assertFalse(form.is_valid())
        self.message.statut = 'envoye'
        self.message.save()
        self.client.post(url, {'meta_template': ''})
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.template_meta_name, 'intro')

    def configure(self):
        self.campaign.template_meta_name = 'intro'
        self.campaign.template_meta_language = 'fr'
        self.campaign.template_meta_params = ['{{prenom}}']
        self.campaign.template_meta_preview = 'Bonjour {{1}}'
        self.campaign.save()

    @patch('whatsapp_agent.services.WhatsAppService.envoyer_message')
    @patch('whatsapp_agent.meta_templates.approved_templates', return_value=[TEMPLATE])
    def test_test_and_both_delivery_paths_use_saved_template(self, catalog, send):
        self.configure()
        send.return_value = {'success': True, 'message_id': 'wamid.test', 'erreur': ''}
        self.client.post(reverse('whatsapp_agent:wa_test', args=[self.campaign.pk]),
            {'numero_test': '+237699000002'})
        self.assertEqual(send.call_args.kwargs, {'template_name': 'intro', 'template_language': 'fr', 'template_params': ['Leonel']})
        _traiter_message_direct(self.message)
        self.assertEqual(send.call_args.kwargs['template_params'], ['Leonel'])
        envoyer_message_task.run(self.message.pk)
        self.assertEqual(send.call_args.kwargs['template_name'], 'intro')
        self.assertEqual(send.call_args.kwargs['template_language'], 'fr')

    @patch('whatsapp_agent.views.validate_selection', side_effect=TemplateError('Modele suspendu'))
    @patch('whatsapp_agent.views.lancer_campagne_task.delay')
    def test_unavailable_template_blocks_launch(self, launch, validate):
        self.configure()
        self.client.post(reverse('whatsapp_agent:wa_lancer', args=[self.campaign.pk]), {'confirm_launch': 'on'})
        launch.assert_not_called()

    def test_catalog_requires_staff(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('whatsapp_agent:wa_api_templates_meta')).status_code, 302)
