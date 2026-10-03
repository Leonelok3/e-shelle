"""Public editorial content, independent of member data and profile availability."""
HOME_DESCRIPTION = ('Rencontres locales et internationales entre adultes en Afrique, en Europe et au Canada. '
                    'Créez votre profil sur E-Shelle Love et échangez après match.')
COMMON_FAQ = [
    {'question': 'Peut-on faire des rencontres locales et internationales ?',
     'answer': 'Oui. Les horizons Ma ville, Afrique, Europe, Canada et Sans frontières orientent la découverte. '
               'Vous pouvez préciser un pays de résidence, une ville et une langue. Les profils proposés dépendent '
               'des membres inscrits et des préférences réciproques.'},
    {'question': 'Faut-il payer pour commencer une conversation ?',
     'answer': 'Le compte gratuit permet de créer un profil, d’ajouter des photos, de découvrir des profils et de liker '
               'dans les limites quotidiennes. Après un match réciproque, la messagerie est disponible sans quota quotidien. '
               'Les pass proposent des options supplémentaires.'},
    {'question': 'Quand mon profil et mes photos deviennent-ils visibles ?',
     'answer': 'Les photos sont publiées dès leur ajout après les contrôles du fichier. Un profil actif avec une photo '
               'peut apparaître selon les préférences des autres membres. Le mode discret et les blocages peuvent limiter '
               'cette visibilité. Une photo publiée ne constitue pas une vérification d’identité.'},
    {'question': 'Comment aborder une rencontre à distance ?',
     'answer': 'Parlez de vos attentes, de vos langues et des horaires qui vous conviennent. Prenez le temps de vous connaître. '
               'N’envoyez pas d’argent à une personne rencontrée en ligne et ne partagez pas de documents personnels. '
               'Pour une première rencontre, choisissez un lieu public et prévenez un proche.'},
]
SEO_PAGES = {
    'international': {
        'route': 'seo_international', 'path': 'rencontre-internationale/',
        'title': 'Rencontres internationales : Afrique, Europe et Canada',
        'h1': 'Votre histoire peut commencer ici. Et continuer ailleurs.', 'city': 'Local & international',
        'intro': 'E-Shelle Love relie les envies de rencontre entre l’Afrique, l’Europe et le Canada. Découvrez une personne '
                 'dans votre ville ou au-delà des frontières, selon vos affinités et vos préférences.',
        'points': ['Choisissez votre horizon : votre ville, un continent ou le Canada.',
                   'Précisez une langue pour faciliter les premiers échanges.', 'L’intérêt doit être réciproque pour discuter.'],
        'sections': [('Des affinités avant des kilomètres', 'Une langue partagée, des passions et une vision de la relation '
                      'peuvent lancer une conversation malgré la distance. Le score de compatibilité est un repère calculé '
                      'à partir des informations du profil, pas une promesse de relation.'),
                     ('Une rencontre à distance se construit à deux', 'Dites si vous recherchez une relation locale ou si '
                      'vous êtes ouvert à la distance. Parlez des horaires, des attentes et des possibilités réalistes '
                      'de vous rencontrer, sans précipiter un voyage.')],
    },
    'afrique': {
        'route': 'seo_afrique', 'path': 'rencontre-afrique/',
        'title': 'Rencontres en Afrique et avec la diaspora', 'h1': 'Des racines à partager. Des histoires à inventer.', 'city': 'Afrique',
        'intro': 'Rencontrez des adultes en Afrique et ouvrez la conversation avec la diaspora en Europe et au Canada. '
                 'E-Shelle Love vous laisse choisir la proximité, les langues et les affinités qui comptent pour vous.',
        'points': ['Explorez l’horizon Afrique ou choisissez un pays de résidence.',
                   'Vos langues et vos passions trouvent leur place dans votre profil.', 'Sans frontières permet de découvrir aussi la diaspora.'],
        'sections': [('Un continent, des parcours différents', 'De Dakar à Douala, d’Abidjan à Casablanca, les attentes '
                      'et les histoires sont personnelles. Présentez vos envies et choisissez une ville ou un pays '
                      'dans les filtres. Aucun volume de profils dans une ville n’est garanti.'),
                     ('La diaspora, un lien vivant', 'Vivre à l’étranger n’efface pas vos attaches. Votre nationalité '
                      'et votre pays de résidence sont distincts : la découverte utilise votre résidence.')],
    },
    'europe': {
        'route': 'seo_europe', 'path': 'rencontre-europe/',
        'title': 'Rencontres en Europe et avec la diaspora africaine', 'h1': 'Une nouvelle ville. De nouvelles affinités.', 'city': 'Europe',
        'intro': 'En France, en Belgique, en Suisse ou ailleurs en Europe, découvrez des personnes qui partagent vos envies '
                 'de rencontre. E-Shelle Love rapproche aussi les parcours entre l’Europe et l’Afrique.',
        'points': ['Filtrez par pays de résidence, pas par nationalité.', 'Choisissez une ville et une langue.',
                   'Explorez aussi l’Afrique et le Canada avec Sans frontières.'],
        'sections': [('Rencontrer dans votre quotidien', 'Votre ville peut être un premier point de rencontre. Une passion '
                      'ou une langue peuvent être un autre. Ma ville sélectionne le même pays de résidence et la même '
                      'ville déclarée ; il ne calcule pas un rayon GPS.'),
                     ('Des parcours qui se croisent', 'Installé depuis longtemps ou arrivé récemment, décrivez ce que '
                      'vous recherchez et choisissez votre rythme. Une origine commune n’est pas une obligation pour découvrir un profil.')],
    },
    'canada': {
        'route': 'seo_canada', 'path': 'rencontre-canada/',
        'title': 'Rencontres au Canada et avec la diaspora africaine', 'h1': 'Au Canada, faites de la place à une belle rencontre.', 'city': 'Canada',
        'intro': 'À Montréal, Québec, Toronto ou ailleurs au Canada, commencez par une conversation qui vous ressemble. '
                 'E-Shelle Love permet aussi de découvrir des profils en Afrique et en Europe.',
        'points': ['L’horizon Canada sélectionne les profils qui y déclarent leur résidence.',
                   'Précisez votre ville et une langue dans les filtres gratuits.', 'La messagerie s’ouvre après un intérêt réciproque.'],
        'sections': [('Votre résidence compte pour la découverte', 'Un membre de la diaspora peut indiquer le Canada '
                      'comme résidence tout en gardant sa nationalité. Le filtre Canada utilise cette résidence ; '
                      'la disponibilité dépend des membres inscrits.'),
                     ('Un rythme qui respecte la distance', 'Pour une conversation avec l’Afrique ou l’Europe, convenez '
                      'ensemble d’un horaire. Partagez vos intentions sans promettre un déplacement ou une installation '
                      'avant de vous connaître.')],
    },
    'cameroun': {
        'route': 'seo_cameroun', 'path': 'rencontre-serieuse-cameroun/',
        'title': 'Rencontres sérieuses au Cameroun et avec la diaspora',
        'h1': 'Au Cameroun ou dans la diaspora, partagez plus qu’un bonjour.', 'city': 'Cameroun',
        'intro': 'Découvrez des profils au Cameroun selon vos préférences, puis ouvrez votre horizon à la diaspora '
                 'en Europe et au Canada. E-Shelle Love accompagne les premiers échanges entre adultes.',
        'points': ['Choisissez le Cameroun comme pays de résidence.', 'Affinez par ville, âge et langue.',
                   'Échangez gratuitement avec vos matchs.'],
        'sections': [('Proximité ou ouverture internationale', 'Pour une rencontre dans votre ville, choisissez Ma ville. '
                      'Si vous êtes ouvert à la distance, essayez Sans frontières et décrivez cette envie dans votre profil.'),
                     ('Votre sourire, votre personnalité', 'Une photo récente et quelques détails sur vos passions '
                      'permettent de vous présenter. Les photos apparaissent dès leur ajout, sans attendre une validation administrative.')],
    },
    'douala': {
        'route': 'seo_douala', 'path': 'rencontre-serieuse-douala/',
        'title': 'Rencontres sérieuses à Douala', 'h1': 'À Douala, commencez une conversation qui compte.', 'city': 'Douala',
        'intro': 'Vous vivez à Douala et souhaitez faire une rencontre sérieuse ? Présentez vos envies sur E-Shelle Love '
                 'et explorez les profils selon votre ville, vos langues et vos préférences.',
        'points': ['Précisez Cameroun et Douala dans les filtres.', 'Découvrez les profils avant d’exprimer votre intérêt.',
                   'Un match réciproque ouvre la conversation.'],
        'sections': [('Une première rencontre dans la ville', 'Après avoir échangé, choisissez ensemble un lieu public '
                      'que vous connaissez et prévenez un proche. Chacun doit pouvoir décider librement de se rencontrer.'),
                     ('De Douala à la diaspora', 'Vous pouvez explorer les horizons Europe et Canada. Parlez dès le départ '
                      'de ce que signifie la distance pour vous, sans présumer des intentions de l’autre.')],
    },
    'yaounde': {
        'route': 'seo_yaounde', 'path': 'rencontre-serieuse-yaounde/',
        'title': 'Rencontres sérieuses à Yaoundé', 'h1': 'À Yaoundé, laissez une nouvelle histoire commencer.', 'city': 'Yaoundé',
        'intro': 'Découvrez des personnes à Yaoundé qui correspondent à vos préférences de rencontre. Sur E-Shelle Love, '
                 'vos passions et votre vision de la relation donnent du sens au premier message.',
        'points': ['Précisez votre ville et votre pays de résidence.', 'Partagez vos passions dans le profil.',
                   'Gardez le contrôle avec le blocage et le signalement.'],
        'sections': [('La proximité, à votre rythme', 'Ma ville propose les membres qui déclarent la même ville et le '
                      'même pays de résidence. Leur présence dépend des inscriptions et des préférences réciproques.'),
                     ('Un premier message personnel', 'Une passion ou une langue partagée peut être un bon point de '
                      'départ. Le Coach Love peut vous aider à trouver une formulation respectueuse.')],
    },
}


def destination_links():
    return [{'label': page['city'], 'route': page['route']} for page in SEO_PAGES.values()]


def public_routes():
    return ['accueil', 'premium', 'securite'] + [page['route'] for page in SEO_PAGES.values()]
