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
        pending = PhotoProfil.objects.create(profil=self.a, image='pending.webp')
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
