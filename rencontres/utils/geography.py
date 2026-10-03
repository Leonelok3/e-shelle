"""Residence and discovery horizons shared by forms, views and matching."""

HORIZONS = [
    ('monde', 'Sans frontières', 'bi-globe2'),
    ('ma_ville', 'Ma ville', 'bi-geo-alt'),
    ('afrique', 'Afrique', 'bi-sun'),
    ('europe', 'Europe', 'bi-compass'),
    ('canada', 'Canada', 'bi-map'),
]

AFRICA = (
    'Afrique du Sud', 'Algérie', 'Angola', 'Bénin', 'Botswana', 'Burkina Faso',
    'Burundi', 'Cameroun', 'Cap-Vert', 'Comores', 'Congo', 'Congo-Brazzaville',
    'RDC', 'République démocratique du Congo', 'Congo-Kinshasa', "Côte d'Ivoire",
    'Djibouti', 'Égypte', 'Érythrée', 'Eswatini', 'Éthiopie', 'Gabon', 'Gambie',
    'Ghana', 'Guinée', 'Guinée-Bissau', 'Guinée équatoriale', 'Kenya', 'Lesotho',
    'Liberia', 'Libye', 'Madagascar', 'Malawi', 'Mali', 'Maroc', 'Maurice',
    'Mauritanie', 'Mozambique', 'Namibie', 'Niger', 'Nigeria', 'Ouganda',
    'République centrafricaine', 'Rwanda', 'Sao Tomé-et-Principe', 'Sénégal',
    'Seychelles', 'Sierra Leone', 'Somalie', 'Soudan', 'Soudan du Sud',
    'Tanzanie', 'Tchad', 'Togo', 'Tunisie', 'Zambie', 'Zimbabwe',
)
EUROPE = (
    'Albanie', 'Allemagne', 'Andorre', 'Autriche', 'Belgique', 'Biélorussie',
    'Bosnie-Herzégovine', 'Bulgarie', 'Chypre', 'Croatie', 'Danemark',
    'Espagne', 'Estonie', 'Finlande', 'France', 'Grèce', 'Hongrie', 'Irlande',
    'Islande', 'Italie', 'Lettonie', 'Liechtenstein', 'Lituanie', 'Luxembourg',
    'Macédoine du Nord', 'Malte', 'Moldavie', 'Monaco', 'Monténégro', 'Norvège',
    'Pays-Bas', 'Pologne', 'Portugal', 'Roumanie', 'Royaume-Uni', 'Russie',
    'Saint-Marin', 'Serbie', 'Slovaquie', 'Slovénie', 'Suède', 'Suisse',
    'Tchéquie', 'République tchèque', 'Ukraine', 'Vatican',
)


def horizon_context(request):
    selected = request.session.get('filtres_rencontre', {}).get('horizon') or 'monde'
    return {
        'horizons': [{'value': value, 'label': label, 'icon': icon} for value, label, icon in HORIZONS],
        'horizon_selectionne': selected,
    }
