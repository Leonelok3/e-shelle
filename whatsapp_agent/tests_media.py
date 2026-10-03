import hashlib
import hmac
import json
from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch
from pathlib import Path

import requests
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import ContactWhatsApp, ConversationWhatsApp, MessageWhatsApp
from .media import private_storage, download_attachment, validate_upload


class AttachmentTests(TestCase):
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
    def test_inbox_renders_attachment_controls_and_endpoints(self):
        response = self.client.get(reverse('whatsapp_agent:wa_inbox'), {'conv': self.conversation.pk})
        self.assertContains(response, 'id="wa-file-input"')
        self.assertContains(response, 'id="wa-attach-button"')
        self.assertContains(response, f'data-send-url="{self.url}"')
        self.assertContains(response, 'inbox-media.js?v=20261003-1')

    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings_override = override_settings(WHATSAPP_PRIVATE_MEDIA_ROOT=self.temp.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.user = get_user_model().objects.create_user(username='operator', is_staff=True)
        self.client.force_login(self.user)
        self.contact = ContactWhatsApp.objects.create(numero='+237699112233')
        self.conversation = ConversationWhatsApp.objects.create(contact=self.contact)
        self.incoming = MessageWhatsApp.objects.create(conversation=self.conversation, texte='Bonjour')
        self.url = reverse('whatsapp_agent:wa_api_repondre', args=[self.conversation.pk])
        self.post_patcher = patch('whatsapp_agent.media.requests.post')
        self.post = self.post_patcher.start()
        self.addCleanup(self.post_patcher.stop)
        self.get_patcher = patch('whatsapp_agent.media.requests.get')
        self.get = self.get_patcher.start()
        self.addCleanup(self.get_patcher.stop)
        self.post.side_effect = [self.response({'id': 'media-123'}), self.response({'messages': [{'id': 'wamid.file'}]})]

    def response(self, data, status=200):
        result = Mock(status_code=status)
        result.json.return_value = data
        return result

    def pdf(self, name='Devis.pdf'):
        return SimpleUploadedFile(name, b'%PDF-1.4\nTest attachment\n%%EOF', content_type='application/pdf')

    def image(self):
        output = BytesIO()
        Image.new('RGB', (300, 300)).save(output, format='PNG')
        return SimpleUploadedFile('photo.png', output.getvalue(), content_type='image/png')

    def test_document_upload_and_send_with_caption_preserves_filename(self):
        response = self.client.post(self.url, {'fichier': self.pdf('Devis été.pdf'), 'texte': 'Votre devis'})
        self.assertEqual(response.status_code, 200, response.content)
        message = self.conversation.messages.get(direction='sortant')
        self.assertEqual(message.media_filename, 'Devis été.pdf')
        self.assertEqual(message.texte, 'Votre devis')
        self.assertEqual(message.whatsapp_msg_id, 'wamid.file')
        self.assertEqual(message.media_id, 'media-123')
        self.assertTrue(message.media_url.startswith('private:'))
        self.assertTrue(private_storage().exists(message.media_url.removeprefix('private:')))
        upload, send = self.post.call_args_list
        self.assertEqual(upload.args[0], 'https://graph.facebook.com/v23.0/123/media')
        self.assertEqual(upload.kwargs['data']['messaging_product'], 'whatsapp')
        self.assertEqual(send.kwargs['json']['document'], {'id': 'media-123', 'filename': 'Devis été.pdf', 'caption': 'Votre devis'})

    def test_image_is_sent_as_image_without_document_filename(self):
        self.assertEqual(self.client.post(self.url, {'fichier': self.image()}).status_code, 200)
        payload = self.post.call_args.kwargs['json']
        self.assertEqual(payload['type'], 'image')
        self.assertEqual(payload['image'], {'id': 'media-123'})

    def test_refused_upload_is_failed_without_sending_a_message(self):
        self.post.side_effect = [self.response({'error': {'code': 131053, 'message': 'Unsupported file'}}, 400)]
        response = self.client.post(self.url, {'fichier': self.pdf()})
        self.assertEqual(response.status_code, 502)
        self.assertEqual(self.post.call_count, 1)
        self.assertEqual(self.conversation.messages.get(direction='sortant').statut, 'echec')
        self.assertIn('131053', response.json()['erreur'])

    def test_send_refusal_never_claims_delivery(self):
        self.post.side_effect = [self.response({'id': 'media-123'}), self.response({'error': {'code': 131047}}, 400)]
        response = self.client.post(self.url, {'fichier': self.pdf()})
        self.assertEqual(response.status_code, 502)
        self.assertIn('24 heures', response.json()['erreur'])
        self.assertEqual(self.conversation.messages.get(direction='sortant').statut, 'echec')

    def test_network_timeout_records_failure_without_claiming_delivery(self):
        self.post.side_effect = requests.Timeout()
        self.assertEqual(self.client.post(self.url, {'fichier': self.pdf()}).status_code, 502)
        self.assertEqual(self.conversation.messages.get(direction='sortant').statut, 'echec')

    def test_invalid_files_and_oversize_do_not_call_meta(self):
        for file in [SimpleUploadedFile('test.html', b'<html/>'),
                     SimpleUploadedFile('bad.pdf', b'<script>alert(1)</script>'),
                     SimpleUploadedFile('empty.pdf', b'')]:
            with self.subTest(name=file.name):
                self.assertEqual(self.client.post(self.url, {'fichier': file}).status_code, 400)
        with override_settings(WHATSAPP_ATTACHMENT_MAX_MB=0):
            self.assertEqual(self.client.post(self.url, {'fichier': self.pdf()}).status_code, 400)
        self.post.assert_not_called()
        self.assertFalse(self.conversation.messages.filter(direction='sortant').exists())

    def test_audio_caption_is_rejected_instead_of_silently_discarded(self):
        audio = SimpleUploadedFile('sound.mp3', b'ID3test-audio', content_type='audio/mpeg')
        response = self.client.post(self.url, {'fichier': audio, 'texte': 'Ne pas perdre ce texte'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('séparément', response.json()['erreur'])
        self.post.assert_not_called()

    def test_closed_customer_window_is_explicit(self):
        MessageWhatsApp.objects.filter(pk=self.incoming.pk).update(meta_timestamp=timezone.now()-timedelta(hours=25))
        response = self.client.post(self.url, {'fichier': self.pdf()})
        self.assertEqual(response.status_code, 400)
        self.assertIn('24 heures', response.json()['erreur'])
        self.post.assert_not_called()

    @override_settings(WHATSAPP_DRY_RUN=True)
    def test_simulation_never_sends_and_has_its_own_status(self):
        response = self.client.post(self.url, {'fichier': self.pdf()})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['simulation'])
        self.assertEqual(self.conversation.messages.get(direction='sortant').statut, 'simulation')
        self.post.assert_not_called()

    def test_authentication_csrf_and_post_are_required(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.user)
        self.assertEqual(strict.post(self.url, {'fichier': self.pdf()}).status_code, 403)
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.client.post(self.url, {'fichier': self.pdf()}).status_code, 302)
        self.post.assert_not_called()

    def test_private_download_preserves_unicode_filename_and_is_not_public(self):
        self.client.post(self.url, {'fichier': self.pdf('Devis été.pdf')})
        msg = self.conversation.messages.get(direction='sortant')
        response = self.client.get(msg.media_download_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4\nTest attachment\n%%EOF')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertIn('filename*=', response['Content-Disposition'])
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.client.logout()
        self.assertEqual(self.client.get(msg.media_download_url).status_code, 302)

    def configure_download(self):
        metadata = self.response({'url': 'https://lookaside.fbsbx.com/whatsapp_business/attachments/?id=1',
                                 'mime_type': 'application/pdf', 'file_size': 12})
        file = self.response({})
        file.iter_content.return_value = [b'%PDF-content']
        context = Mock()
        context.__enter__ = Mock(return_value=file)
        context.__exit__ = Mock(return_value=False)
        self.get.side_effect = [metadata, context]

    def test_meta_download_uses_configured_version_and_private_storage(self):
        self.configure_download()
        path = download_attachment('incoming-id', 'document', 'contrat.pdf')
        self.assertTrue(path.startswith('private:'), path)
        self.assertEqual(self.get.call_args_list[0].args[0], 'https://graph.facebook.com/v23.0/incoming-id')
        self.assertFalse(self.get.call_args.kwargs['allow_redirects'])
        with private_storage().open(path.removeprefix('private:'), 'rb') as file:
            self.assertEqual(file.read(), b'%PDF-content')

    def test_download_will_not_forward_token_to_an_untrusted_host(self):
        self.get.side_effect = [self.response({'url': 'https://example.com/file.pdf'})]
        self.assertEqual(download_attachment('media-id'), '')
        self.assertEqual(self.get.call_count, 1)

    def test_legacy_media_id_download_is_retried_and_then_cached(self):
        msg = MessageWhatsApp.objects.create(conversation=self.conversation, media_type='document', media_url='12345', texte='devis.pdf')
        self.get.side_effect = requests.Timeout()
        self.assertEqual(self.client.get(msg.media_download_url).status_code, 404)
        self.configure_download()
        response = self.client.get(msg.media_download_url)
        self.assertEqual(response.status_code, 200)
        b''.join(response.streaming_content)
        msg.refresh_from_db()
        self.assertTrue(msg.media_url.startswith('private:'))
        self.get.reset_mock()
        response = self.client.get(msg.media_download_url)
        self.assertEqual(response.status_code, 200)
        b''.join(response.streaming_content)
        self.get.assert_not_called()

    def test_signed_document_webhook_is_fast_deduplicated_and_keeps_metadata(self):
        value = {'contacts': [{'wa_id': '237699112233', 'profile': {'name': 'Client'}}],
            'messages': [{'from': '237699112233', 'id': 'wamid.incoming', 'timestamp': str(int(timezone.now().timestamp())),
            'type': 'document', 'document': {'id': 'incoming-id', 'filename': 'Contrat signé.pdf',
                                            'caption': 'À vérifier', 'mime_type': 'application/pdf'}}]}
        body = json.dumps({'object': 'whatsapp_business_account', 'entry': [{'changes': [{'value': value}]}]})
        signature = 'sha256=' + hmac.new(b'test-secret', body.encode(), hashlib.sha256).hexdigest()
        for _ in range(2):
            self.assertEqual(self.client.post(reverse('whatsapp_agent:wa_webhook'), body,
                content_type='application/json', HTTP_X_HUB_SIGNATURE_256=signature).status_code, 200)
        msg = MessageWhatsApp.objects.get(whatsapp_msg_id='wamid.incoming')
        self.assertEqual(msg.media_filename, 'Contrat signé.pdf')
        self.assertEqual(msg.texte, 'À vérifier')
        self.assertIsNotNone(msg.meta_timestamp)
        self.get.assert_not_called()
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.non_lus_count, 1)

    def test_history_returns_authenticated_links_and_not_private_paths(self):
        self.client.post(self.url, {'fichier': self.pdf()})
        response = self.client.get(reverse('whatsapp_agent:wa_api_conv_detail', args=[self.conversation.pk]))
        data = response.json()
        msg = data['messages'][-1]
        self.assertTrue(msg['media_download_url'].startswith('/whatsapp/media/'))
        self.assertNotIn('private:', response.content.decode())
        self.assertEqual(msg['display_filename'], 'Devis.pdf')

    def test_text_reply_still_works_with_multipart(self):
        self.post.side_effect = [self.response({'messages': [{'id': 'wamid.text'}]})]
        self.assertEqual(self.client.post(self.url, {'texte': 'Bonjour'}).status_code, 200)
        msg = self.conversation.messages.get(direction='sortant')
        self.assertFalse(msg.has_media)

    def test_file_type_validation_rejects_renamed_images(self):
        file = self.image()
        file.name = 'renamed.jpg'
        with self.assertRaises(ValidationError):
            validate_upload(file)
