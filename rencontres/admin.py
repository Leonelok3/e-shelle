from django.contrib import admin
from django.utils.html import format_html
from django.utils.html import mark_safe
from django.utils import timezone

from rencontres.models import (
    ProfilRencontre, PhotoProfil, Like, Match, Blocage,
    Conversation, Message, PlanPremiumRencontre, AbonnementRencontre,
    Signalement
)


@admin.register(ProfilRencontre)
class ProfilRencontreAdmin(admin.ModelAdmin):
    list_display = [
        'prenom_affiche', 'user', 'genre', 'age_display', 'ville',
        'pays', 'photo_status', 'est_verifie', 'est_premium', 'est_actif',
        'profil_complet', 'derniere_connexion'
    ]
    list_filter = ['genre', 'est_verifie', 'est_premium', 'est_actif', 'pays', 'religion', 'est_diaspora']
    search_fields = ['prenom_affiche', 'user__email', 'user__username', 'ville']
    readonly_fields = ['derniere_connexion', 'vues_profil', 'profil_complet', 'date_creation']
    actions = ['verifier_profils', 'suspendre_profils', 'reactiver_profils', 'activer_premium_test']

    fieldsets = (
        ('Identité', {
            'fields': ('user', 'prenom_affiche', 'date_naissance', 'genre', 'orientation')
        }),
        ('Localisation', {
            'fields': ('pays', 'ville', 'latitude', 'longitude', 'nationalite', 'est_diaspora', 'pays_residence')
        }),
        ('Origine', {
            'fields': ('origine_ethnique',)
        }),
        ('Apparence', {
            'fields': ('taille_cm', 'morphologie', 'teint', 'photo_principale')
        }),
        ('Situation personnelle', {
            'fields': ('situation_matrimoniale', 'a_des_enfants', 'nb_enfants', 'veut_des_enfants')
        }),
        ('Formation & travail', {
            'fields': ('niveau_etude', 'profession', 'revenus')
        }),
        ('Religion', {
            'fields': ('religion', 'pratique_religieuse')
        }),
        ('À propos', {
            'fields': ('biographie', 'ce_que_je_cherche', 'interets', 'langues')
        }),
        ('Recherche partenaire', {
            'fields': ('recherche_age_min', 'recherche_age_max', 'recherche_genre',
                       'recherche_pays', 'recherche_religion', 'recherche_distance_km')
        }),
        ('Statut', {
            'fields': ('est_verifie', 'badge_verifie', 'est_actif', 'est_premium',
                       'profil_complet', 'vues_profil', 'derniere_connexion', 'date_creation')
        }),
        ('Confidentialité', {
            'fields': ('afficher_en_ligne', 'afficher_distance', 'qui_peut_ecrire')
        }),
    )

    def age_display(self, obj):
        try:
            return f"{obj.age()} ans"
        except Exception:
            return "—"
    age_display.short_description = "Âge"

    def photo_status(self, obj):
        approved = obj.photos.filter(est_approuvee=True).count()
        pending = obj.photos.filter(est_approuvee=False).count()
        if approved:
            return format_html('<span style="color:#22c55e;font-weight:700">{} approuvée(s)</span>', approved)
        if pending:
            return format_html('<span style="color:#f59e0b;font-weight:700">{} en attente</span>', pending)
        return format_html('<span style="color:#ef4444;font-weight:700">Aucune</span>')
    photo_status.short_description = "Photos"

    @admin.action(description="Vérifier les profils sélectionnés")
    def verifier_profils(self, request, queryset):
        queryset.update(est_verifie=True, badge_verifie=True)
        self.message_user(request, f"{queryset.count()} profil(s) vérifiés.")

    @admin.action(description="Suspendre les profils sélectionnés")
    def suspendre_profils(self, request, queryset):
        queryset.update(est_actif=False)
        self.message_user(request, f"{queryset.count()} profil(s) suspendus.")

    @admin.action(description="Réactiver les profils sélectionnés")
    def reactiver_profils(self, request, queryset):
        queryset.update(est_actif=True)
        self.message_user(request, f"{queryset.count()} profil(s) réactivés.")

    @admin.action(description="Activer le premium (test 30j)")
    def activer_premium_test(self, request, queryset):
        from rencontres.models import PlanPremiumRencontre, AbonnementRencontre
        plan = PlanPremiumRencontre.objects.filter(nom='platinum').first()
        if not plan:
            self.message_user(request, "Plan 1 mois introuvable.", level='error')
            return
        for profil in queryset:
            AbonnementRencontre.objects.create(
                profil=profil,
                plan=plan,
                date_fin=timezone.now() + timezone.timedelta(days=plan.duree_jours)
            )
        self.message_user(request, f"{queryset.count()} profil(s) passés en premium ({plan.duree_jours}j).")


@admin.register(PhotoProfil)
class PhotoProfilAdmin(admin.ModelAdmin):
    list_display = ['profil', 'est_approuvee', 'est_principale', 'ordre', 'date_ajout', 'image_preview']
    list_filter = ['est_approuvee', 'est_principale']
    actions = ['approuver_photos', 'rejeter_photos']

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" height="60" style="border-radius:4px;"/>')
        return "—"
    image_preview.short_description = "Aperçu"

    @admin.action(description="Approuver les photos sélectionnées")
    def approuver_photos(self, request, queryset):
        for photo in queryset.select_related('profil'):
            photo.est_approuvee = True
            photo.save(update_fields=['est_approuvee'])
            profil = photo.profil
            if photo.est_principale or not profil.photo_principale:
                profil.photo_principale = photo.image
            profil.est_verifie = True
            profil.badge_verifie = True
            profil.calculer_completion()
            profil.save(update_fields=[
                'photo_principale', 'est_verifie', 'badge_verifie', 'profil_complet'
            ])
        self.message_user(request, f"{queryset.count()} photo(s) approuvée(s).")

    @admin.action(description="Rejeter (supprimer) les photos sélectionnées")
    def rejeter_photos(self, request, queryset):
        count = queryset.count()
        for photo in queryset.select_related('profil'):
            if photo.profil.photo_principale == photo.image:
                photo.profil.photo_principale = None
                photo.profil.save(update_fields=['photo_principale'])
        queryset.delete()
        self.message_user(request, f"{count} photo(s) supprimée(s).")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['envoyeur', 'recepteur', 'type_like', 'date_like', 'est_lu']
    list_filter = ['type_like', 'est_lu']
    search_fields = ['envoyeur__prenom_affiche', 'recepteur__prenom_affiche']


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['profil_1', 'profil_2', 'date_match', 'est_actif', 'score_compatibilite']
    list_filter = ['est_actif']
    search_fields = ['profil_1__prenom_affiche', 'profil_2__prenom_affiche']


@admin.register(PlanPremiumRencontre)
class PlanPremiumRencontreAdmin(admin.ModelAdmin):
    list_display = [
        'plan_badge', 'duree_jours', 'prix_xaf_display',
        'likes_par_jour', 'messages_par_jour', 'photos_max',
        'filtre_avance', 'mode_incognito',
    ]
    ordering = ['duree_jours', 'prix_xaf_mensuel']

    fieldsets = (
        ('🏷️ Identité du plan', {
            'fields': ('nom', 'description'),
            'description': '3 jours · 10 jours · 1 mois'
        }),
        ('💰 Tarification FCFA (Mobile Money)', {
            'fields': ('prix_xaf_mensuel', 'duree_jours'),
            'description': 'Paiement manuel : le client paie, puis l’admin active après vérification.'
        }),
        ('📊 Limites d\'utilisation', {
            'fields': ('likes_par_jour', 'super_likes_par_jour', 'messages_par_jour', 'photos_max', 'boost_profil_par_semaine'),
            'description': 'Mettre -1 pour illimité.'
        }),
        ('✨ Fonctionnalités incluses', {
            'fields': ('peut_voir_qui_a_like', 'peut_rembobiner', 'badge_premium',
                       'filtre_avance', 'sans_publicite', 'mode_incognito', 'stats_profil'),
        }),
    )

    def plan_badge(self, obj):
        colors = {'silver': '#9CA3AF', 'gold': '#F59E0B', 'platinum': '#8B5CF6'}
        icons  = {'silver': '⚡', 'gold': '💗', 'platinum': '👑'}
        color  = colors.get(obj.nom, '#666')
        icon   = icons.get(obj.nom, '⭐')
        return format_html(
            '<span style="color:{};font-weight:800;font-size:1rem">{} {}</span>',
            color, icon, obj.get_nom_display()
        )
    plan_badge.short_description = 'Plan'
    plan_badge.admin_order_field = 'nom'

    def prix_xaf_display(self, obj):
        return format_html('<strong>{:,} FCFA</strong>', int(obj.prix_xaf_mensuel)).replace(',', ' ')
    prix_xaf_display.short_description = 'Prix'
    prix_xaf_display.admin_order_field = 'prix_xaf_mensuel'


@admin.register(AbonnementRencontre)
class AbonnementRencontreAdmin(admin.ModelAdmin):
    list_display = [
        'profil', 'plan', 'demande_status', 'payment_reference',
        'telephone_paiement', 'reference_client', 'statut_transaction',
        'date_debut', 'date_fin', 'jours_restants_display'
    ]
    list_filter = ['est_actif', 'plan', 'date_debut']
    search_fields = [
        'profil__prenom_affiche', 'profil__user__username',
        'payment_reference', 'profil__user__email'
    ]
    readonly_fields = [
        'payment_reference', 'telephone_paiement',
        'reference_client', 'statut_transaction'
    ]
    date_hierarchy = 'date_debut'
    actions = ['activer_abonnements', 'desactiver_abonnements']

    fieldsets = (
        ('Demande', {
            'fields': ('profil', 'plan', 'est_actif', 'date_fin')
        }),
        ('Paiement manuel', {
            'fields': (
                'payment_reference', 'telephone_paiement',
                'reference_client', 'statut_transaction'
            ),
            'description': (
                'Verifier le paiement Mobile Money, puis utiliser l’action '
                '"Activer manuellement les abonnements sélectionnés".'
            )
        }),
        ('Options', {
            'fields': ('renouvellement_auto',)
        }),
    )

    def _transaction(self, obj):
        if not obj.payment_reference:
            return None
        try:
            from payments.models import Transaction
            return Transaction.objects.filter(reference=obj.payment_reference).first()
        except Exception:
            return None

    def demande_status(self, obj):
        if obj.est_valide():
            return format_html('<span style="color:#22c55e;font-weight:800">Actif</span>')
        if obj.est_actif and obj.date_fin <= timezone.now():
            return format_html('<span style="color:#ef4444;font-weight:800">Expiré</span>')
        return format_html('<span style="color:#f59e0b;font-weight:800">En attente</span>')
    demande_status.short_description = "Statut"
    demande_status.admin_order_field = 'est_actif'

    def telephone_paiement(self, obj):
        tx = self._transaction(obj)
        return tx.telephone if tx and tx.telephone else "—"
    telephone_paiement.short_description = "Téléphone"

    def reference_client(self, obj):
        tx = self._transaction(obj)
        if tx and isinstance(tx.metadata, dict):
            return tx.metadata.get('reference_client') or "—"
        return "—"
    reference_client.short_description = "Référence client"

    def statut_transaction(self, obj):
        tx = self._transaction(obj)
        if not tx:
            return "—"
        colors = {
            'succes': '#22c55e',
            'en_attente': '#f59e0b',
            'initie': '#94a3b8',
            'echec': '#ef4444',
        }
        return format_html(
            '<span style="color:{};font-weight:700">{}</span>',
            colors.get(tx.statut, '#94a3b8'),
            tx.get_statut_display(),
        )
    statut_transaction.short_description = "Transaction"

    def jours_restants_display(self, obj):
        return f"{obj.jours_restants()} jours"
    jours_restants_display.short_description = "Jours restants"

    @admin.action(description="Activer manuellement les abonnements sélectionnés")
    def activer_abonnements(self, request, queryset):
        count = 0
        for abo in queryset.select_related('profil', 'plan'):
            AbonnementRencontre.objects.filter(
                profil=abo.profil,
                est_actif=True,
            ).exclude(pk=abo.pk).update(est_actif=False)
            abo.est_actif = True
            abo.date_fin = timezone.now() + timezone.timedelta(days=abo.plan.duree_jours)
            abo.save(update_fields=['est_actif', 'date_fin'])
            abo.profil.est_premium = True
            abo.profil.save(update_fields=['est_premium'])
            if abo.payment_reference:
                try:
                    from payments.models import Transaction
                    Transaction.objects.filter(reference=abo.payment_reference).update(statut='succes')
                except Exception:
                    pass
            count += 1
        self.message_user(request, f"{count} abonnement(s) activé(s).")

    @admin.action(description="Désactiver les abonnements sélectionnés")
    def desactiver_abonnements(self, request, queryset):
        profils = []
        for abo in queryset.select_related('profil'):
            abo.est_actif = False
            abo.save(update_fields=['est_actif'])
            profils.append(abo.profil)
        for profil in profils:
            has_active = AbonnementRencontre.objects.filter(
                profil=profil,
                est_actif=True,
                date_fin__gt=timezone.now(),
            ).exists()
            profil.est_premium = has_active
            profil.save(update_fields=['est_premium'])
        self.message_user(request, f"{queryset.count()} abonnement(s) désactivé(s).")


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    list_display = ['signaleur', 'signale', 'raison', 'date_signalement', 'est_traite', 'action_prise']
    list_filter = ['raison', 'est_traite']
    search_fields = ['signaleur__prenom_affiche', 'signale__prenom_affiche']
    actions = ['marquer_traites', 'suspendre_signales']

    @admin.action(description="Marquer comme traités")
    def marquer_traites(self, request, queryset):
        queryset.update(
            est_traite=True, action_prise='ignore',
            traite_par=request.user, date_traitement=timezone.now()
        )
        self.message_user(request, f"{queryset.count()} signalement(s) traités.")

    @admin.action(description="Suspendre les profils signalés")
    def suspendre_signales(self, request, queryset):
        profils = set(s.signale for s in queryset)
        for p in profils:
            p.est_actif = False
            p.save(update_fields=['est_actif'])
        queryset.update(
            est_traite=True, action_prise='suspension_temp',
            traite_par=request.user, date_traitement=timezone.now()
        )
        self.message_user(request, f"{len(profils)} profil(s) suspendu(s).")
