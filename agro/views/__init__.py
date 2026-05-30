from .catalogue_views import accueil_agro, catalogue, categorie, detail_produit
from .acteur_views import (
    inscription_acteur, profil_public, modifier_profil,
    annuaire_acteurs, annuaire_par_type,
    mes_produits, ajouter_produit, modifier_produit,
    supprimer_produit, gerer_photos_produit,
)
from .offre_views import (
    liste_offres, creer_offre, detail_offre,
    liste_ao, lancer_ao, detail_ao, repondre_ao,
)
from .commande_views import (
    demander_devis, mes_devis, detail_devis,
    repondre_devis, accepter_devis,
    mes_commandes, detail_commande,
    exporter_devis_pdf, exporter_facture,
)
from .dashboard_views import (
    dashboard, stats_dashboard,
    mes_certifications, mes_avis,
    page_premium, souscrire,
    signaler_produit, signaler_acteur,
)
from .recherche_views import (
    recherche,
    ajax_recherche, ajax_favoris,
    ajax_contact, ajax_convertir, ajax_stats_produit,
)
from .intelligence_views import (
    marketplace_agro, assistant_ia_agro, prix_marche_agro,
    dashboard_producteur_agro, commander_produit_agro,
)
