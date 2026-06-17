from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from rencontres.models import Conversation, Like, Match, Message, ProfilRencontre
from rencontres.utils.matching_algo import calculer_score_compatibilite


class Command(BaseCommand):
    help = "Cree 10 profils de demo E-Shelle Love avec matchs et messages."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password",
            default="LoveDemo123!",
            help="Mot de passe commun des comptes de demo.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        password = options["password"]
        User = get_user_model()

        profiles_data = [
            {
                "username": "love_demo_amina",
                "email": "amina.love@demo.local",
                "prenom": "Amina",
                "birth": date(1997, 5, 14),
                "genre": "femme",
                "recherche_genre": "homme",
                "ville": "Douala",
                "pays": "Cameroun",
                "lat": 4.0511,
                "lon": 9.7679,
                "profession": "Responsable marketing",
                "religion": "chretien",
                "langues": ["Français", "Anglais", "Ewondo"],
                "interets": ["Voyage", "Cuisine", "Entrepreneuriat", "Musique"],
                "bio": "Souriante, ambitieuse, j'aime les projets sérieux et les discussions simples.",
                "cherche": "Une relation stable avec quelqu'un de respectueux et tourné vers l'avenir.",
            },
            {
                "username": "love_demo_eric",
                "email": "eric.love@demo.local",
                "prenom": "Eric",
                "birth": date(1993, 9, 2),
                "genre": "homme",
                "recherche_genre": "femme",
                "ville": "Yaounde",
                "pays": "Cameroun",
                "lat": 3.848,
                "lon": 11.5021,
                "profession": "Ingenieur logiciel",
                "religion": "chretien",
                "langues": ["Français", "Anglais"],
                "interets": ["Technologie", "Fitness", "Voyage", "Lecture"],
                "bio": "Calme, curieux, passionne par la tech et les voyages.",
                "cherche": "Une personne vraie, avec qui construire tranquillement.",
            },
            {
                "username": "love_demo_fatou",
                "email": "fatou.love@demo.local",
                "prenom": "Fatou",
                "birth": date(1995, 1, 22),
                "genre": "femme",
                "recherche_genre": "homme",
                "ville": "Dakar",
                "pays": "Sénégal",
                "lat": 14.7167,
                "lon": -17.4677,
                "profession": "Pharmacienne",
                "religion": "musulman",
                "langues": ["Français", "Wolof"],
                "interets": ["Cuisine", "Famille", "Lecture", "Bénévolat"],
                "bio": "Je crois aux relations fondees sur le respect et la famille.",
                "cherche": "Un homme mature, sincere et stable.",
            },
            {
                "username": "love_demo_jean",
                "email": "jean.love@demo.local",
                "prenom": "Jean",
                "birth": date(1990, 11, 8),
                "genre": "homme",
                "recherche_genre": "femme",
                "ville": "Abidjan",
                "pays": "Côte d'Ivoire",
                "lat": 5.36,
                "lon": -4.0083,
                "profession": "Entrepreneur",
                "religion": "chretien",
                "langues": ["Français", "Dioula"],
                "interets": ["Entrepreneuriat", "Sport", "Musique", "Voyage"],
                "bio": "Entrepreneur, positif, j'aime apprendre et avancer.",
                "cherche": "Une relation serieuse avec de la complicite.",
            },
            {
                "username": "love_demo_mireille",
                "email": "mireille.love@demo.local",
                "prenom": "Mireille",
                "birth": date(1989, 3, 30),
                "genre": "femme",
                "recherche_genre": "homme",
                "ville": "Paris",
                "pays": "France",
                "lat": 48.8566,
                "lon": 2.3522,
                "profession": "Infirmiere",
                "religion": "chretien",
                "langues": ["Français", "Anglais"],
                "interets": ["Famille", "Voyage", "Cuisine", "Photographie"],
                "bio": "Diaspora camerounaise, attachee aux valeurs et a la famille.",
                "cherche": "Quelqu'un de responsable, avec une vraie vision de vie.",
                "diaspora": True,
                "pays_residence": "France",
            },
            {
                "username": "love_demo_patrick",
                "email": "patrick.love@demo.local",
                "prenom": "Patrick",
                "birth": date(1987, 7, 19),
                "genre": "homme",
                "recherche_genre": "femme",
                "ville": "Bruxelles",
                "pays": "Belgique",
                "lat": 50.8503,
                "lon": 4.3517,
                "profession": "Consultant finance",
                "religion": "chretien",
                "langues": ["Français", "Anglais"],
                "interets": ["Lecture", "Voyage", "Entrepreneuriat", "Fitness"],
                "bio": "Installe en Europe, je reste tres connecte a l'Afrique.",
                "cherche": "Une femme elegante, simple et serieuse.",
                "diaspora": True,
                "pays_residence": "Belgique",
            },
            {
                "username": "love_demo_nadia",
                "email": "nadia.love@demo.local",
                "prenom": "Nadia",
                "birth": date(1999, 12, 5),
                "genre": "femme",
                "recherche_genre": "homme",
                "ville": "Bafoussam",
                "pays": "Cameroun",
                "lat": 5.4778,
                "lon": 10.4176,
                "profession": "Commercante",
                "religion": "chretien",
                "langues": ["Français", "Bamiléké"],
                "interets": ["Mode", "Danse", "Cuisine", "Famille"],
                "bio": "Simple, travailleuse et joyeuse. J'aime les personnes honnetes.",
                "cherche": "Une relation claire, sans jeux.",
            },
            {
                "username": "love_demo_serge",
                "email": "serge.love@demo.local",
                "prenom": "Serge",
                "birth": date(1994, 4, 17),
                "genre": "homme",
                "recherche_genre": "femme",
                "ville": "Douala",
                "pays": "Cameroun",
                "lat": 4.0615,
                "lon": 9.7862,
                "profession": "Medecin",
                "religion": "chretien",
                "langues": ["Français", "Anglais"],
                "interets": ["Sport", "Lecture", "Bénévolat", "Nature"],
                "bio": "Professionnel de sante, respectueux, plutot pose.",
                "cherche": "Une femme authentique et bienveillante.",
            },
            {
                "username": "love_demo_grace",
                "email": "grace.love@demo.local",
                "prenom": "Grace",
                "birth": date(1992, 8, 11),
                "genre": "femme",
                "recherche_genre": "homme",
                "ville": "Montreal",
                "pays": "Canada",
                "lat": 45.5017,
                "lon": -73.5673,
                "profession": "Data analyst",
                "religion": "spirituel",
                "langues": ["Français", "Anglais"],
                "interets": ["Technologie", "Yoga", "Voyage", "Art"],
                "bio": "Curieuse, creative, j'aime les conversations profondes.",
                "cherche": "Une connexion sincere, ouverte et respectueuse.",
                "diaspora": True,
                "pays_residence": "Canada",
            },
            {
                "username": "love_demo_mamadou",
                "email": "mamadou.love@demo.local",
                "prenom": "Mamadou",
                "birth": date(1991, 2, 26),
                "genre": "homme",
                "recherche_genre": "femme",
                "ville": "Bamako",
                "pays": "Mali",
                "lat": 12.6392,
                "lon": -8.0029,
                "profession": "Architecte",
                "religion": "musulman",
                "langues": ["Français", "Dioula"],
                "interets": ["Art", "Photographie", "Nature", "Famille"],
                "bio": "Creatif et familial. Je prends le temps de connaitre les gens.",
                "cherche": "Une femme serieuse, douce et ambitieuse.",
            },
        ]

        profiles = []
        for item in profiles_data:
            user, _ = User.objects.get_or_create(
                username=item["username"],
                defaults={
                    "email": item["email"],
                    "first_name": item["prenom"],
                    "role": "CLIENT",
                    "ville": item["ville"],
                },
            )
            user.email = item["email"]
            user.first_name = item["prenom"]
            user.ville = item["ville"]
            user.role = "CLIENT"
            user.set_password(password)
            user.save()

            profil, _ = ProfilRencontre.objects.update_or_create(
                user=user,
                defaults={
                    "prenom_affiche": item["prenom"],
                    "date_naissance": item["birth"],
                    "genre": item["genre"],
                    "orientation": "heterosexuel",
                    "pays": item["pays"],
                    "ville": item["ville"],
                    "latitude": item["lat"],
                    "longitude": item["lon"],
                    "origine_ethnique": "Africain(e)",
                    "nationalite": item["pays"],
                    "est_diaspora": item.get("diaspora", False),
                    "pays_residence": item.get("pays_residence", item["pays"]),
                    "taille_cm": 165 if item["genre"] == "femme" else 178,
                    "morphologie": "normale",
                    "teint": "naturel",
                    "situation_matrimoniale": "celibataire",
                    "a_des_enfants": False,
                    "nb_enfants": 0,
                    "veut_des_enfants": "peut_etre",
                    "niveau_etude": "licence",
                    "profession": item["profession"],
                    "revenus": "moyen",
                    "religion": item["religion"],
                    "pratique_religieuse": "pratiquant",
                    "langues": item["langues"],
                    "biographie": item["bio"],
                    "ce_que_je_cherche": item["cherche"],
                    "interets": item["interets"],
                    "recherche_age_min": 25,
                    "recherche_age_max": 45,
                    "recherche_genre": item["recherche_genre"],
                    "recherche_distance_km": 20000,
                    "est_verifie": True,
                    "badge_verifie": True,
                    "est_actif": True,
                    "profil_complet": 100,
                    "afficher_en_ligne": True,
                    "afficher_distance": True,
                    "qui_peut_ecrire": "matchs",
                },
            )
            profil.calculer_completion()
            profiles.append(profil)

        pairs = [
            ("love_demo_amina", "love_demo_eric"),
            ("love_demo_fatou", "love_demo_mamadou"),
            ("love_demo_mireille", "love_demo_patrick"),
            ("love_demo_nadia", "love_demo_serge"),
            ("love_demo_grace", "love_demo_jean"),
        ]

        for left_username, right_username in pairs:
            left = ProfilRencontre.objects.get(user__username=left_username)
            right = ProfilRencontre.objects.get(user__username=right_username)
            Like.objects.get_or_create(envoyeur=left, recepteur=right)
            Like.objects.get_or_create(envoyeur=right, recepteur=left)
            first, second = sorted([left, right], key=lambda p: p.id)
            match, _ = Match.objects.get_or_create(
                profil_1=first,
                profil_2=second,
                defaults={
                    "score_compatibilite": calculer_score_compatibilite(left, right)["score_total"],
                },
            )
            conv, _ = Conversation.objects.get_or_create(match=match)
            samples = [
                (left, f"Salut {right.prenom_affiche}, ton profil m'a beaucoup plu."),
                (right, f"Merci {left.prenom_affiche}. J'ai aussi aime ta presentation."),
                (left, "On peut discuter un peu pour faire connaissance ?"),
            ]
            if conv.messages.count() == 0:
                for sender, text in samples:
                    Message.objects.create(conversation=conv, expediteur=sender, contenu=text)
                conv.dernier_message_at = timezone.now()
                conv.save(update_fields=["dernier_message_at"])

        self.stdout.write(self.style.SUCCESS("10 profils Love crees/mis a jour."))
        self.stdout.write(self.style.SUCCESS(f"Mot de passe commun: {password}"))
        self.stdout.write(self.style.SUCCESS("Matchs de demo: 5 | Conversations avec messages: 5"))
