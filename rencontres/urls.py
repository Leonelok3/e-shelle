from django.urls import path
from rencontres import views

app_name = 'rencontres'

urlpatterns = [
    # Entrée dans l'app
    path('', views.accueil_rencontre, name='accueil'),
    path('rencontre-serieuse-cameroun/', views.seo_landing, {'slug': 'cameroun'}, name='seo_cameroun'),
    path('rencontre-serieuse-douala/', views.seo_landing, {'slug': 'douala'}, name='seo_douala'),
    path('rencontre-serieuse-yaounde/', views.seo_landing, {'slug': 'yaounde'}, name='seo_yaounde'),

    # Profil
    path('profil/creer/', views.creer_profil, name='creer_profil'),
    path('profil/modifier/', views.modifier_profil, name='modifier_profil'),
    path('profil/<int:pk>/', views.detail_profil, name='detail_profil'),
    path('profil/photos/', views.gerer_photos, name='gerer_photos'),

    # Découverte
    path('decouverte/', views.decouverte, name='decouverte'),
    path('filtres/', views.filtres, name='filtres'),

    # Actions AJAX
    path('ajax/like/<int:profil_id>/', views.ajax_like, name='ajax_like'),
    path('ajax/passer/<int:profil_id>/', views.ajax_passer, name='ajax_passer'),
    path('ajax/profils/', views.ajax_charger_profils, name='ajax_profils'),
    path('ajax/stats/', views.ajax_stats_profil, name='ajax_stats'),
    path('ajax/notifications/', views.ajax_check_notifications, name='ajax_notifications'),

    # Coach IA
    path('coach/', views.coach_love, name='coach'),

    # Matchs
    path('matchs/', views.liste_matchs, name='matchs'),
    path('matchs/<int:match_id>/', views.detail_match, name='detail_match'),
    path('match/nouveau/<int:match_id>/', views.popup_nouveau_match, name='nouveau_match'),
    path('qui-maime/', views.qui_maime, name='qui_maime'),

    # Messagerie
    path('messages/', views.inbox, name='inbox'),
    path('messages/<int:conversation_id>/', views.conversation, name='conversation'),
    path('ajax/envoyer-message/', views.ajax_envoyer_message, name='ajax_message'),
    path('ajax/marquer-lu/<int:conv_id>/', views.ajax_marquer_lu, name='ajax_marquer_lu'),

    # Premium
    path('premium/', views.page_premium, name='premium'),
    path('premium/souscrire/<str:plan>/', views.souscrire_premium, name='souscrire'),
    path('boost/', views.activer_boost, name='boost'),

    # Paramètres et sécurité
    path('parametres/', views.parametres_rencontre, name='parametres'),
    path('bloquer/<int:profil_id>/', views.bloquer_profil, name='bloquer'),
    path('signaler/<int:profil_id>/', views.signaler_profil, name='signaler'),
    path('desactiver/', views.desactiver_compte_rencontre, name='desactiver'),

    # Modération (staff)
    path('moderation/', views.moderation_photos, name='moderation'),
]
