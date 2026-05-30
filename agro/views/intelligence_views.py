from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..models import (
    ActeurAgro,
    DemandeDevis,
    PrixMarche,
    ProduitAgro,
    QuestionAgentIA,
    StockProducteur,
)


AGENTS_IA = [
    {
        'key': 'agricole',
        'nom': 'Agent agricole',
        'icone': 'bi-flower1',
        'description': 'Conseils sur manioc, mais, banane plantain, arachide, cacao et palmier.',
        'exemple': 'Ma feuille de manioc jaunit, que faire ?',
    },
    {
        'key': 'maladies',
        'nom': 'Maladies & photos',
        'icone': 'bi-camera',
        'description': 'Analyse indicative de feuilles, fruits et tiges a partir de photos.',
        'exemple': 'Cette feuille de plantain est tachee, que faire ?',
    },
    {
        'key': 'marche',
        'nom': 'Agent marche',
        'icone': 'bi-graph-up-arrow',
        'description': 'Prix locaux, villes prioritaires, opportunites de vente et alertes.',
        'exemple': 'Ou vendre mon mais aujourd hui au meilleur prix ?',
    },
    {
        'key': 'finance',
        'nom': 'Finance & stock',
        'icone': 'bi-wallet2',
        'description': 'Calculs de stock, besoin en semences, tresorerie et microcredit.',
        'exemple': 'Quel pret puis-je rembourser avec mes ventes ?',
    },
]


def _reponse_agent(agent_type, question):
    texte = question.lower()
    if agent_type == 'maladies':
        culture = 'manioc' if 'manioc' in texte else 'plantain' if 'plantain' in texte else 'culture'
        return (
            f"Diagnostic indicatif pour {culture}: isolez les plants les plus atteints, "
            "retirez les feuilles tres abimees, evitez l exces d eau et prenez une photo nette "
            "du dessus et du dessous des feuilles. Consultez un technicien agricole si les taches "
            "progressent en 48 a 72 heures."
        )
    if agent_type == 'marche':
        return (
            "A Douala et Yaounde, les meilleurs prix se negocient souvent tot le matin sur les "
            "marches de gros. Comparez Bafoussam si vous avez du plantain ou du mais, et regroupez "
            "le transport pour ameliorer votre marge."
        )
    if agent_type == 'finance':
        return (
            "Commencez avec un petit credit remboursable sur 4 a 8 semaines. Gardez au moins 30% "
            "de vos ventes prevues pour le transport, les pertes et les frais Mobile Money avant "
            "de fixer votre mensualite."
        )
    return (
        "Pour le manioc, le mais ou le plantain, verifiez d abord l humidite du sol, la couleur "
        "des feuilles et la presence d insectes. Programmez le semis au debut d une periode humide, "
        "utilisez des semences propres et evitez de vendre toute la recolte le meme jour si le prix baisse."
    )


def marketplace_agro(request):
    produits = ProduitAgro.objects.filter(statut='publie').select_related('acteur', 'categorie').prefetch_related('photos')
    paginator = Paginator(produits, 12)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    return render(request, 'agro/marketplace.html', {
        'page_obj': page_obj,
        'total': produits.count(),
        'page_title': 'Marketplace AgroConnect AI Cameroun',
    })


def assistant_ia_agro(request):
    question_active = None
    if request.method == 'POST':
        agent_type = request.POST.get('agent_type', 'agricole')
        question = request.POST.get('question', '').strip()
        if not question:
            messages.error(request, "Posez une question a l'agent IA.")
            return redirect('agro:assistant_ia')

        reponse = _reponse_agent(agent_type, question)
        question_active = QuestionAgentIA.objects.create(
            utilisateur=request.user if request.user.is_authenticated else None,
            agent_type=agent_type,
            question=question,
            image=request.FILES.get('image'),
            reponse=reponse,
        )
        messages.success(request, "L'agent IA a prepare une recommandation indicative.")

    historique = QuestionAgentIA.objects.all()
    if request.user.is_authenticated:
        historique = historique.filter(utilisateur=request.user)
    else:
        historique = historique.none()

    return render(request, 'agro/assistant_ia.html', {
        'agents': AGENTS_IA,
        'question_active': question_active,
        'historique': historique[:6],
        'page_title': 'Assistant IA agricole | AgroConnect AI',
    })


def prix_marche_agro(request):
    ville = request.GET.get('ville', '')
    produit = request.GET.get('produit', '')
    prix = PrixMarche.objects.all()
    if ville:
        prix = prix.filter(ville__icontains=ville)
    if produit:
        prix = prix.filter(produit__icontains=produit)

    villes = PrixMarche.objects.values_list('ville', flat=True).distinct().order_by('ville')
    produits = PrixMarche.objects.values_list('produit', flat=True).distinct().order_by('produit')

    return render(request, 'agro/prix_marche.html', {
        'prix_marche': prix,
        'villes': villes,
        'produits': produits,
        'ville_active': ville,
        'produit_actif': produit,
        'page_title': 'Prix du marche | AgroConnect AI',
    })


@login_required
def dashboard_producteur_agro(request):
    try:
        acteur = request.user.profil_agro
    except ActeurAgro.DoesNotExist:
        messages.info(request, "Completez votre profil agro pour activer le dashboard producteur.")
        return redirect('agro:inscription')

    produits = ProduitAgro.objects.filter(acteur=acteur).select_related('categorie')
    stocks = StockProducteur.objects.filter(utilisateur=request.user).select_related('produit')
    revenus_estimes = produits.aggregate(total=Sum('prix_unitaire'))['total'] or Decimal('0')
    devis_recents = DemandeDevis.objects.filter(vendeur=acteur).select_related('acheteur', 'produit')[:5]

    stats = {
        'produits': produits.count(),
        'commandes': DemandeDevis.objects.filter(vendeur=acteur).count(),
        'stock': sum(stock.quantite for stock in stocks),
        'revenus': revenus_estimes,
    }

    return render(request, 'agro/dashboard/producteur_ai.html', {
        'acteur': acteur,
        'stats': stats,
        'produits': produits[:6],
        'stocks': stocks[:6],
        'devis_recents': devis_recents,
        'alertes': [
            'Plantain: prix en hausse a Douala cette semaine.',
            'Mais: surveillez le sechage avant stockage long.',
            'Mobile Money: proposez paiement a la livraison pour rassurer les nouveaux acheteurs.',
        ],
        'page_title': 'Dashboard producteur IA | AgroConnect AI',
    })


@login_required
def commander_produit_agro(request, pk):
    produit = get_object_or_404(ProduitAgro.objects.select_related('acteur'), pk=pk, statut='publie')
    try:
        acheteur = request.user.profil_agro
    except ActeurAgro.DoesNotExist:
        messages.info(request, "Creez votre profil acheteur avant de commander.")
        return redirect('agro:inscription')

    if request.method == 'POST':
        quantite = float(request.POST.get('quantite') or produit.quantite_min_commande)
        ville_livraison = request.POST.get('ville_livraison', acheteur.ville)
        telephone = request.POST.get('telephone', acheteur.telephone)
        message = request.POST.get('message', '')

        DemandeDevis.objects.create(
            acheteur=acheteur,
            vendeur=produit.acteur,
            produit=produit,
            quantite=quantite,
            unite_mesure=produit.unite_mesure,
            destination=ville_livraison,
            message=f"Commande marketplace. Telephone: {telephone}. {message}".strip(),
        )
        messages.success(request, "Demande envoyee au vendeur. Paiement MTN/Orange Money pret a brancher.")
        return redirect('agro:mes_devis')

    return render(request, 'agro/commander.html', {
        'produit': produit,
        'page_title': f'Commander {produit.nom} | E-Shelle Agro',
    })
