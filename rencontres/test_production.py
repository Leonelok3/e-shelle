from datetime import date, timedelta
from io import BytesIO
from tempfile import TemporaryDirectory
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rencontres.models import ProfilRencontre, PhotoProfil, PlanPremiumRencontre, AbonnementRencontre, Like, Match, Conversation, Message, Blocage
from rencontres.utils.access import entitlements, sync_premium
from rencontres.utils.matching_algo import get_profils_compatibles
from rencontres.utils.notifications import verifier_limite_likes, verifier_limite_messages
from rencontres.utils.subscriptions import approve_subscription
from rencontres.forms.profile_forms import PhotoProfilForm, ProfilRencontreForm
from payments.models import Transaction


@override_settings(SECURE_SSL_REDIRECT=False, ALLOWED_HOSTS=['testserver'], STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class LoveProductionTests(TestCase):
    def setUp(self):
        self.a = self.profile('alice', 'femme')
        self.b = self.profile('bob', 'homme')
        self.client.force_login(self.a.user)
        self.plan = PlanPremiumRencontre.objects.get(nom='gold')

    def profile(self, name, gender, **extra):
        user = get_user_model().objects.create_user(username=name, password='test-love-2026')
        defaults = dict(prenom_affiche=name, date_naissance=date(1995, 6, 1), genre=gender,
            pays='Cameroun', ville='Douala', nationalite='Camerounaise', situation_matrimoniale='celibataire',
            veut_des_enfants='oui', niveau_etude='licence')
        defaults.update(extra)
        p = ProfilRencontre.objects.create(user=user, **defaults)
        PhotoProfil.objects.create(profil=p, image=f'rencontres/{name}.webp', est_approuvee=True)
        p.refresh_from_db()
        return p

    def subscribe(self, profil=None, days=10):
        return AbonnementRencontre.objects.create(profil=profil or self.a, plan=self.plan,
            date_fin=timezone.now() + timedelta(days=days))

    def chat(self):
        match = Match.objects.create(profil_1=self.a, profil_2=self.b)
        return Conversation.objects.create(match=match)

    def test_expired_pass_and_free_messaging(self):
        self.subscribe(days=-1)
        ProfilRencontre.objects.filter(pk=self.a.pk).update(est_premium=True)
        self.a.refresh_from_db()
        self.assertFalse(sync_premium(self.a))
        self.assertEqual(entitlements(self.a)['photos_max'], 6)
        self.assertEqual(verifier_limite_messages(self.a), (True, -1))
        self.assertEqual(verifier_limite_likes(self.a), (True, 15))

    def test_plan_specific_limits(self):
        self.plan.super_likes_par_jour = 1
        self.plan.save()
        self.subscribe()
        Like.objects.create(envoyeur=self.a, recepteur=self.b, type_like='super_like')
        self.assertEqual(verifier_limite_likes(self.a, 'super_like'), (False, 0))

    def test_filters_privacy_and_incognito(self):
        self.assertTrue(get_profils_compatibles(self.a))
        self.assertEqual(get_profils_compatibles(self.a, filters={'pays': 'Canada'}), [])
        self.assertEqual(get_profils_compatibles(self.a)[0][2], None)
        self.subscribe(self.b)
        self.b.incognito = True
        self.b.save()
        self.assertEqual(get_profils_compatibles(self.a), [])
        self.b.abonnements.update(date_fin=timezone.now() - timedelta(days=1))
        self.assertTrue(get_profils_compatibles(self.a))

    def test_like_rejects_self_and_blocked(self):
        url = reverse('rencontres:ajax_like', args=[self.a.pk])
        self.assertEqual(self.client.post(url, '{}', content_type='application/json').status_code, 403)
        Blocage.objects.create(bloqueur=self.b, bloque=self.a)
        url = reverse('rencontres:ajax_like', args=[self.b.pk])
        self.assertEqual(self.client.post(url, '{}', content_type='application/json').status_code, 403)

    def test_mutual_like_creates_single_chat(self):
        Like.objects.create(envoyeur=self.b, recepteur=self.a)
        url = reverse('rencontres:ajax_like', args=[self.b.pk])
        result = self.client.post(url, '{}', content_type='application/json')
        self.assertTrue(result.json()['est_match'])
        self.client.post(url, '{}', content_type='application/json')
        self.assertEqual(Conversation.objects.count(), 1)

    def test_poll_receives_first_message_and_blocks_access(self):
        conv = self.chat()
        msg = Message.objects.create(conversation=conv, expediteur=self.b, contenu='Bonjour')
        url = reverse('rencontres:ajax_messages', args=[conv.pk])
        self.assertEqual(self.client.get(url).json()['messages'][0]['id'], msg.pk)
        self.assertEqual(self.client.get(url, {'since': msg.pk}).json()['messages'], [])
        self.assertEqual(self.client.get(url, {'since': 'oops'}).status_code, 400)
        Blocage.objects.create(bloqueur=self.b, bloque=self.a)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse('rencontres:conversation', args=[conv.pk])).status_code, 404)
        result = self.client.post(reverse('rencontres:ajax_message'), {'conversation_id': conv.pk, 'contenu': 'Non'}, content_type='application/json')
        self.assertEqual(result.status_code, 403)

    def test_inactive_match_and_outsider_cannot_read(self):
        conv = self.chat()
        c = self.profile('carol', 'femme')
        self.client.force_login(c.user)
        self.assertEqual(self.client.get(reverse('rencontres:ajax_messages', args=[conv.pk])).status_code, 404)
        self.client.force_login(self.a.user)
        conv.match.est_actif = False
        conv.match.save()
        self.assertEqual(self.client.get(reverse('rencontres:conversation', args=[conv.pk])).status_code, 404)

    def test_payment_request_validation_dedup_and_approval(self):
        url = reverse('rencontres:souscrire', args=['gold'])
        result = self.client.post(url, {'telephone': 'bad', 'methode': 'carte'})
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Transaction.objects.count(), 0)
        data = {'telephone': '+237 699 123 456', 'methode': 'orange'}
        self.client.post(url, data)
        self.client.post(url, data)
        self.assertEqual(Transaction.objects.count(), 1)
        abo = AbonnementRencontre.objects.get(profil=self.a)
        self.assertFalse(abo.est_actif)
        approved = approve_subscription(abo.pk)
        end = approved.date_fin
        self.assertEqual(approve_subscription(abo.pk).date_fin, end)
        self.assertFalse(approved.renouvellement_auto)

    def test_boost_quota_and_rewind(self):
        self.subscribe()
        url = reverse('rencontres:boost')
        self.client.post(url)
        self.client.post(url)
        self.a.refresh_from_db()
        self.assertEqual(len(self.a.boost_utilisations), 1)
        self.assertGreater(self.a.boost_fin, timezone.now())
        session = self.client.session
        session['profils_passes'] = [self.b.pk]
        session.save()
        self.assertTrue(self.client.post(reverse('rencontres:ajax_rembobiner')).json()['success'])
        self.assertEqual(self.client.session['profils_passes'], [])

    def test_photo_deletion_resyncs_main_and_no_identity_badge(self):
        photo = PhotoProfil.objects.create(profil=self.a, image='second.webp', est_approuvee=True)
        self.a.photos.exclude(pk=photo.pk).delete()
        self.a.refresh_from_db()
        self.assertEqual(self.a.photo_principale.name, 'second.webp')
        self.assertFalse(self.a.badge_verifie)
        photo.delete()
        self.a.refresh_from_db()
        self.assertFalse(self.a.photo_principale)

    def test_photo_validation_and_compression(self):
        def upload(size):
            out = BytesIO(); Image.new('RGB', size).save(out, format='PNG')
            return SimpleUploadedFile('portrait.png', out.getvalue(), content_type='image/png')
        small = PhotoProfilForm(files={'image': upload((100, 100))})
        self.assertFalse(small.is_valid())
        valid = PhotoProfilForm(files={'image': upload((1800, 1800))})
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(valid.cleaned_data['image'].content_type, 'image/webp')
        self.assertEqual(Image.open(valid.cleaned_data['image']).size, (1600, 1600))

    def test_underage_form_rejected(self):
        form = ProfilRencontreForm(data={'date_naissance': '2015-01-01'})
        self.assertFalse(form.is_valid())
        self.assertIn('date_naissance', form.errors)

    def test_upload_immediately_publishes_profile_and_main_photo(self):
        self.b.photos.all().delete()
        self.assertEqual(get_profils_compatibles(self.a), [])
        self.client.force_login(self.b.user)
        out = BytesIO()
        Image.new('RGB', (400, 400)).save(out, format='PNG')
        with TemporaryDirectory() as media, override_settings(MEDIA_ROOT=media):
            result = self.client.post(reverse('rencontres:gerer_photos'), {
                'image': SimpleUploadedFile('portrait.png', out.getvalue(), content_type='image/png')})
            self.assertEqual(result.status_code, 302)
            photo = self.b.photos.get()
            self.assertTrue(photo.est_approuvee)
            self.assertTrue(photo.est_principale)
            self.b.refresh_from_db()
            self.assertEqual(self.b.photo_principale.name, photo.image.name)
            self.assertFalse(self.b.badge_verifie)
            self.assertContains(self.client.get(reverse('rencontres:gerer_photos')), photo.image.url)
            self.client.force_login(self.a.user)
            self.assertEqual(get_profils_compatibles(self.a)[0][0].pk, self.b.pk)
            self.assertContains(self.client.get(reverse('rencontres:detail_profil', args=[self.b.pk])), photo.image.url)
            self.assertEqual(self.client.post(reverse('rencontres:ajax_like', args=[self.b.pk]),
                '{}', content_type='application/json').status_code, 200)

    def test_pending_photo_migration_restores_visibility(self):
        from importlib import import_module
        from types import SimpleNamespace
        from django.apps import apps
        from django.db import connection
        self.b.photos.all().delete()
        photo = PhotoProfil.objects.create(profil=self.b, image='old-pending.webp', est_approuvee=False)
        migrate = import_module('rencontres.migrations.0007_immediate_photo_publication').publish_pending_photos
        migrate(apps, SimpleNamespace(connection=connection))
        migrate(apps, SimpleNamespace(connection=connection))
        photo.refresh_from_db()
        self.b.refresh_from_db()
        self.assertTrue(photo.est_approuvee)
        self.assertTrue(photo.est_principale)
        self.assertEqual(self.b.photo_principale.name, photo.image.name)
        self.assertEqual(self.b.profil_complet, self.b.calculer_completion())
        self.assertFalse(self.b.badge_verifie)
        self.assertEqual(get_profils_compatibles(self.a)[0][0].pk, self.b.pk)

    def test_all_main_pages_render(self):
        for name in ['accueil', 'decouverte', 'premium', 'gerer_photos', 'parametres', 'filtres', 'matchs', 'inbox', 'coach', 'qui_maime']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse('rencontres:' + name)).status_code, 200)
        response = self.client.get(reverse('rencontres:decouverte'))
        self.assertContains(response, 'id="profils-data"')
        self.assertEqual(self.client.get(reverse('rencontres:detail_profil', args=[self.b.pk])).status_code, 200)

    def test_public_pages_and_private_profile(self):
        self.client.logout()
        for name in ['accueil', 'premium', 'securite']:
            self.assertEqual(self.client.get(reverse('rencontres:' + name)).status_code, 200)
        self.assertEqual(self.client.get(reverse('rencontres:detail_profil', args=[self.b.pk])).status_code, 302)

    def test_renewal_preserves_paid_days(self):
        active = self.subscribe()
        payment = Transaction.objects.create(utilisateur=self.a.user, montant=2500, devise='XAF',
            type_tx='abonnement', statut='en_attente', metadata={'plan_rencontre':'gold', 'duree_jours':10})
        pending = AbonnementRencontre.objects.create(profil=self.a, plan=self.plan, est_actif=False,
            date_fin=timezone.now(), payment_reference=payment.reference)
        renewed = approve_subscription(pending.pk)
        self.assertEqual(renewed.date_fin, active.date_fin + timedelta(days=10))
        self.assertEqual(self.a.abonnements.filter(est_actif=True).count(), 1)

    def test_moderation_requires_permission_and_never_verifies_identity(self):
        pending = PhotoProfil.objects.create(profil=self.a, image='pending.webp', est_approuvee=False)
        self.a.user.is_staff = True
        self.a.user.save()
        url = reverse('rencontres:moderation')
        self.assertEqual(self.client.post(url, {'photo_id': pending.pk, 'action': 'approuver'}).status_code, 403)
        self.a.user.is_superuser = True
        self.a.user.save()
        self.assertEqual(self.client.post(url, {'photo_id': pending.pk, 'action': 'approuver'}).status_code, 302)
        self.a.refresh_from_db()
        self.assertFalse(self.a.badge_verifie)

    def test_discovery_escapes_script_payload(self):
        self.b.prenom_affiche = '</script><script>alert(1)</script>'
        self.b.save()
        response = self.client.get(reverse('rencontres:decouverte'))
        self.assertNotContains(response, '</script><script>alert(1)</script>')

    def test_international_horizons_use_residence_and_languages(self):
        self.b.est_diaspora = True
        self.b.pays_residence = ' Canada '
        self.b.ville = 'Montréal'
        self.b.langues = ['Français', 'Anglais']
        self.b.save()
        self.assertEqual(self.b.pays_actuel, 'Canada')
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'afrique'}), [])
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'europe'}), [])
        for filters in [{'horizon': 'canada'}, {'pays': 'Canada'},
                        {'horizon': 'monde', 'ville': 'Montréal', 'langue': 'Français'}]:
            with self.subTest(filters=filters):
                self.assertEqual(get_profils_compatibles(self.a, filters=filters)[0][0].pk, self.b.pk)
        self.assertEqual(get_profils_compatibles(self.a, filters={'langue': 'Espagnol'}), [])
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'ma_ville'}), [])
        self.b.pays_residence = 'France'
        self.b.save()
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'europe'})[0][0].pk, self.b.pk)
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'canada'}), [])

    def test_local_horizon_and_international_blocks(self):
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'ma_ville'})[0][0].pk, self.b.pk)
        self.b.pays = 'France'
        self.b.save()
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'ma_ville'}), [])
        Blocage.objects.create(bloqueur=self.b, bloque=self.a)
        self.assertEqual(get_profils_compatibles(self.a, filters={'horizon': 'europe'}), [])

    def test_horizon_switch_is_post_only_and_keeps_non_geographic_preferences(self):
        session = self.client.session
        session['filtres_rencontre'] = {'pays': 'Cameroun', 'ville': 'Douala', 'distance_km': 20,
                                      'age_min': 25, 'langue': 'Français', 'religion': 'chretien'}
        session.save()
        url = reverse('rencontres:choisir_horizon')
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'horizon': 'invalid'}).status_code, 400)
        self.assertEqual(self.client.post(url, {'horizon': 'canada'}).status_code, 302)
        self.assertEqual(self.client.session['filtres_rencontre'], {
            'horizon': 'canada', 'age_min': 25, 'langue': 'Français', 'religion': 'chretien'})

    def test_international_filters_apply_to_initial_and_ajax_discovery(self):
        self.b.est_diaspora = True
        self.b.pays_residence = 'Canada'
        self.b.save()
        self.client.post(reverse('rencontres:choisir_horizon'), {'horizon': 'canada'})
        response = self.client.get(reverse('rencontres:decouverte'))
        self.assertEqual(response.context['profils_json'][0]['pays'], 'Canada')
        result = self.client.get(reverse('rencontres:ajax_profils')).json()
        self.assertEqual(result['profils'][0]['pays'], 'Canada')
        self.client.post(reverse('rencontres:choisir_horizon'), {'horizon': 'afrique'})
        self.assertEqual(self.client.get(reverse('rencontres:ajax_profils')).json()['profils'], [])

    def test_regional_filter_conflicts_are_explained(self):
        from rencontres.forms.search_forms import FiltresRechercheForm
        form = FiltresRechercheForm({'horizon': 'canada', 'pays': 'France'})
        self.assertFalse(form.is_valid())
        self.assertIn('pays', form.errors)
        form = FiltresRechercheForm({'horizon': 'europe', 'pays': 'Portugal', 'langue': 'Français'})
        self.assertTrue(form.is_valid(), form.errors)

    def test_public_seo_pages_have_canonicals_valid_schema_and_visible_answers(self):
        import json
        import re
        from html import unescape
        from rencontres.seo_content import SEO_PAGES, COMMON_FAQ
        self.client.logout()
        routes = ['accueil'] + [page['route'] for page in SEO_PAGES.values()]
        for route in routes:
            with self.subTest(route=route):
                url = reverse('rencontres:' + route)
                response = self.client.get(url, {'source': 'Canada'})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, f'<link rel="canonical" href="https://e-shelle.com{url}">', html=True)
                self.assertNotContains(response, 'noindex')
                html = response.content.decode()
                data = json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)[1])
                faq = next(item for item in data['@graph'] if item['@type'] == 'FAQPage')
                self.assertEqual(len(faq['mainEntity']), len(COMMON_FAQ))
                visible = re.sub(r'<script.*?</script>', '', html, flags=re.S)
                for question in COMMON_FAQ:
                    self.assertIn(question['question'], unescape(visible))
                    self.assertIn(question['answer'], unescape(visible))
                self.assertContains(response, 'og:image')

    def test_private_love_pages_do_not_expose_structured_member_data(self):
        for route in ['accueil', 'decouverte', 'inbox', 'gerer_photos']:
            response = self.client.get(reverse('rencontres:' + route))
            self.assertContains(response, '<meta name="robots" content="noindex, nofollow">', html=True)
            self.assertNotContains(response, 'application/ld+json')

    def test_seo_json_escapes_html_delimiters(self):
        import json
        from types import SimpleNamespace
        from unittest.mock import patch
        from rencontres.seo_content import SEO_PAGES
        from rencontres.templatetags.love_seo import love_metadata
        page = dict(SEO_PAGES['canada'], title='</script><script>alert(1)</script>')
        request = SimpleNamespace(resolver_match=SimpleNamespace(url_name='seo_canada'), user=self.a.user)
        with patch.dict(SEO_PAGES, {'canada': page}):
            data = love_metadata({'request': request})
        self.assertNotIn('</script>', data['schema'])
        self.assertEqual(json.loads(data['schema'])['@graph'][1]['name'], page['title'])

    def test_love_public_routes_are_in_sitemap_and_private_routes_are_not(self):
        from unittest.mock import patch
        from django.test import RequestFactory
        from seo_agent.services import build_sitemap_entries
        from rencontres.seo_content import public_routes
        with patch('seo_agent.services.LocalSEOAgent.prioritized_pages', return_value=[]):
            entries = build_sitemap_entries(RequestFactory().get('/sitemap.xml'))
        urls = {item['loc'] for item in entries}
        for route in public_routes():
            self.assertIn('https://e-shelle.com' + reverse('rencontres:' + route), urls)
        self.assertFalse(any('/rencontres/profil/' in url or '/rencontres/messages/' in url for url in urls))

    def test_international_coach_respects_real_profile_details(self):
        from rencontres.utils.love_coach import first_messages, compatibility_notes
        self.b.pays = 'Canada'
        self.a.langues = self.b.langues = ['Français']
        messages = first_messages(self.a, self.b)
        self.assertTrue(any('Français' in message for message in messages))
        self.assertTrue(any('moment' in message for message in messages))
        notes = compatibility_notes(self.a, self.b)
        self.assertTrue(any('pays différents' in note for note in notes))
        self.assertFalse(any('meme ville' in note for note in notes))

    def test_robot_rules_keep_love_member_areas_out_of_crawling(self):
        from django.test import RequestFactory
        from seo_agent.views import robots_txt
        response = robots_txt(RequestFactory().get('/robots.txt'))
        text = response.content.decode()
        self.assertIn('Disallow: /rencontres/profil/', text)
        self.assertIn('Disallow: /rencontres/messages/', text)
        self.assertNotIn('Disallow: /rencontres/rencontre-', text)
