"""
E-Shelle Resto — Seed Command
Populates the database with realistic Cameroonian restaurant data.

Usage:
    python manage.py seed_resto
    python manage.py seed_resto --reset  # deletes existing resto data first
"""
from datetime import date, timedelta, time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from resto.models import (
    City, Dish, FoodCategory, MenuCategory,
    Neighborhood, Restaurant, Subscription,
)

User = get_user_model()


# ── Seed data ─────────────────────────────────────────────────────────────────

CITIES_DATA = [
    "Yaoundé",
    "Douala",
    "Bafoussam",
    "Bamenda",
    "Garoua",
    "Kribi",
]

NEIGHBORHOODS_DATA = {
    "Yaoundé": ["Bastos", "Biyem-Assi", "Melen", "Mvog-Ada", "Ngousso"],
    "Douala": [
        "Akwa", "Bonapriso", "Bonanjo", "Makepe", "Deido", "Bonaberi",
        "New-Bell", "Bali", "Ndokoti", "Bepanda", "Kotto", "Logbaba",
        "PK8", "PK10", "PK14", "Yassa", "Cite SIC", "Denver",
        "Ndogbong", "Nyalla", "Village", "Bassa", "Japoma",
    ],
    "Bafoussam": ["Banengo", "Djeleng", "Kamkop", "Tamdja", "Tougang"],
    "Bamenda": ["Commercial Avenue", "Nkwen", "Mile 4", "Old Town", "Up Station"],
    "Garoua": ["Lopéré", "Bourrou", "Poumpoumré", "Yelwa", "Ngong"],
    "Kribi": ["Plage", "Centre Ville", "Dombé", "Grand Batanga", "Talla"],
}

FOOD_CATEGORIES_DATA = [
    ("Cuisine camerounaise", "🍛", 0),
    ("Grillades", "🔥", 1),
    ("Fast food", "🍔", 2),
    ("Poissons & fruits de mer", "🐟", 3),
    ("Végétarien", "🥗", 4),
    ("Boissons", "🥤", 5),
    ("Pâtisserie & desserts", "🥐", 6),
]

RESTAURANTS_DATA = [
    {
        "name": "Chez Mama Fouda",
        "city": "Yaoundé",
        "neighborhood": "Biyem-Assi",
        "address": "Carrefour Biyem-Assi, face au marché",
        "phone": "+237 677 123 456",
        "whatsapp": "+237 677 123 456",
        "description": "La vraie cuisine camerounaise de mama Fouda. Ndolé, Eru, Koki et bien d'autres plats traditionnels préparés avec amour depuis 2005.",
        "categories": ["Cuisine camerounaise"],
        "status": "open",
        "opening_time": time(7, 0),
        "closing_time": time(21, 0),
        "is_featured": True,
        "dishes": [
            {
                "category": "Plats principaux",
                "name": "Ndolé aux crevettes",
                "description": "Notre ndolé signature aux crevettes fraîches du Wouri, servi avec du plantain",
                "price": 2500,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Eru au waterleaf",
                "description": "Feuilles d'okok mijotées avec huile de palme et viande fumée",
                "price": 2000,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Koki de haricots",
                "description": "Gâteau de haricots cuit à la vapeur dans des feuilles de bananier",
                "price": 1000,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Mbongo Tchobi",
                "description": "Poisson braisé en sauce noire épicée, spécialité Bassa",
                "price": 3000,
                "availability": "available",
            },
            {
                "category": "Entrées",
                "name": "Beignets haricots",
                "description": "Beignets de haricots croustillants avec piment",
                "price": 500,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "Jus de gingembre maison",
                "description": "Jus de gingembre frais, citron et miel",
                "price": 500,
                "availability": "available",
            },
        ],
    },
    {
        "name": "Le Grill du Wouri",
        "city": "Douala",
        "neighborhood": "Bonapriso",
        "address": "Avenue de la Liberté, Bonapriso",
        "phone": "+237 699 234 567",
        "whatsapp": "+237 699 234 567",
        "description": "Le meilleur grill de Douala. Poissons et viandes braisés sur charbon de bois, façon traditionnelle bamiléké.",
        "categories": ["Grillades", "Poissons & fruits de mer"],
        "status": "open",
        "opening_time": time(11, 0),
        "closing_time": time(23, 0),
        "is_featured": True,
        "dishes": [
            {
                "category": "Grillades",
                "name": "Poisson braisé capitaine",
                "description": "Capitaine grillé entier avec marinade maison, servi avec plantain et sauce tomate",
                "price": 4500,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Grillades",
                "name": "Poulet braisé demi",
                "description": "Demi-poulet mariné aux épices africaines, grillé au charbon",
                "price": 3500,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Grillades",
                "name": "Côtes de porc braisées",
                "description": "Côtes de porc marinées et grillées lentement",
                "price": 3000,
                "availability": "available",
            },
            {
                "category": "Grillades",
                "name": "Crevettes géantes braisées",
                "description": "6 crevettes géantes grillées à l'ail et au citron",
                "price": 5000,
                "availability": "in_x_minutes",
                "available_in_minutes": 15,
            },
            {
                "category": "Plats principaux",
                "name": "Sanga de maïs",
                "description": "Sanga traditionnelle de maïs blanc avec sauce arachide",
                "price": 1500,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "33 Export Export",
                "description": "Bière camerounaise fraîche",
                "price": 700,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "Eau minérale Supermont",
                "description": "Bouteille 50cl",
                "price": 300,
                "availability": "available",
            },
        ],
    },
    {
        "name": "Restaurant La Saveur des Hauts-Plateaux",
        "city": "Bafoussam",
        "neighborhood": "Banengo",
        "address": "Rond-point de Banengo",
        "phone": "+237 652 345 678",
        "whatsapp": "+237 652 345 678",
        "description": "Cuisine bamiléké authentique. Kondre, Nkui, Mbem — les recettes transmises de génération en génération.",
        "categories": ["Cuisine camerounaise"],
        "status": "open",
        "opening_time": time(8, 0),
        "closing_time": time(20, 30),
        "is_featured": False,
        "dishes": [
            {
                "category": "Plats principaux",
                "name": "Kondre chèvre",
                "description": "Plat traditionnel bamiléké : chèvre et igname pilée cuits ensemble dans un bouillon épicé",
                "price": 3500,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Nkui",
                "description": "Soupe gluante préparée avec des feuilles spéciales, accompagnée de viande",
                "price": 2000,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Mbem (viande de porc séchée)",
                "description": "Porc fumé traditionnel servi avec des haricots",
                "price": 2500,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Poulet DG",
                "description": "Poulet sauté avec plantain mûr et légumes frais",
                "price": 3000,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Entrées",
                "name": "Haricots rouges sauce tomate",
                "description": "Haricots rouges mijotés en sauce tomate et oignon",
                "price": 800,
                "availability": "available",
            },
        ],
    },
    {
        "name": "Fast Corner Douala",
        "city": "Douala",
        "neighborhood": "Akwa",
        "address": "Rue des Palmiers, en face du marché Central",
        "phone": "+237 688 456 789",
        "whatsapp": "+237 688 456 789",
        "description": "Burgers, sandwichs et frites. Cuisine rapide de qualité au cœur d'Akwa.",
        "categories": ["Fast food", "Boissons"],
        "status": "open",
        "opening_time": time(9, 0),
        "closing_time": time(22, 0),
        "is_featured": False,
        "dishes": [
            {
                "category": "Plats principaux",
                "name": "Burger Camerounais",
                "description": "Steak haché, plantain frit, avocat, tomate, sauce piquante maison",
                "price": 2000,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Sandwich poulet grillé",
                "description": "Poulet grillé, laitue, mayonnaise dans une baguette fraîche",
                "price": 1500,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Frites maison",
                "description": "Grosses frites de pomme de terre fraîche",
                "price": 800,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Hot dog",
                "description": "Saucisse grillée, moutarde, ketchup",
                "price": 1000,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "Coca-Cola 35cl",
                "description": "Canette fraîche",
                "price": 500,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "Jus de fruit pasteurisé",
                "description": "Mangue, ananas ou goyave",
                "price": 600,
                "availability": "available",
            },
        ],
    },
    {
        "name": "Chez Tante Marguerite — Kribi Plage",
        "city": "Kribi",
        "neighborhood": "Plage",
        "address": "Boulevard de l'Océan, Kribi Plage",
        "phone": "+237 671 567 890",
        "whatsapp": "+237 671 567 890",
        "description": "Restaurant de plage spécialisé en fruits de mer frais. Homards, crevettes, capitaines pêchés du jour.",
        "categories": ["Poissons & fruits de mer", "Cuisine camerounaise"],
        "status": "open",
        "opening_time": time(10, 0),
        "closing_time": time(21, 0),
        "is_featured": True,
        "dishes": [
            {
                "category": "Plats principaux",
                "name": "Homard grillé (500g)",
                "description": "Homard entier grillé au beurre à l'ail, servi avec frites et salade",
                "price": 8000,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Capitaine frit sauce oignons",
                "description": "Capitaine entier frit croustillant avec sauce aux oignons et poivrons",
                "price": 3500,
                "is_popular": True,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Crevettes sauce gingembre",
                "description": "500g de crevettes sautées au gingembre, ail et citron",
                "price": 4000,
                "availability": "available",
            },
            {
                "category": "Plats principaux",
                "name": "Okok (feuilles de manioc)",
                "description": "Feuilles de manioc pilées avec palme rouge et crevettes",
                "price": 1500,
                "availability": "in_x_minutes",
                "available_in_minutes": 30,
            },
            {
                "category": "Entrées",
                "name": "Salade de fruits de mer",
                "description": "Mélange de crevettes, calmar et poulpe avec vinaigrette citron",
                "price": 2500,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "Cocktail noix de coco fraîche",
                "description": "Eau de noix de coco directement dans la coque",
                "price": 1000,
                "availability": "available",
            },
            {
                "category": "Boissons",
                "name": "Jus de bissap",
                "description": "Boisson fraîche à la fleur d'hibiscus",
                "price": 500,
                "availability": "available",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Peuple la base de données avec des données de test réalistes pour E-Shelle Resto"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Supprime toutes les données resto existantes avant de peupler",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write(self.style.WARNING("Suppression des donnees existantes..."))
            Dish.objects.all().delete()
            MenuCategory.objects.all().delete()
            Restaurant.objects.all().delete()
            Neighborhood.objects.all().delete()
            City.objects.all().delete()
            FoodCategory.objects.all().delete()
            self.stdout.write("Donnees supprimees.")

        # 1. Cities
        self.stdout.write("Creation des villes...")
        cities = {}
        for city_name in CITIES_DATA:
            city, _ = City.objects.get_or_create(
                slug=slugify(city_name),
                defaults={"name": city_name, "is_active": True},
            )
            cities[city_name] = city
        self.stdout.write(self.style.SUCCESS(f"  {len(cities)} villes crees/existantes"))

        # 2. Neighborhoods
        self.stdout.write("Creation des quartiers...")
        neighborhoods = {}
        total_neigh = 0
        for city_name, neigh_list in NEIGHBORHOODS_DATA.items():
            city = cities[city_name]
            for neigh_name in neigh_list:
                neigh_slug = slugify(neigh_name)
                neigh, created = Neighborhood.objects.get_or_create(
                    city=city,
                    slug=neigh_slug,
                    defaults={"name": neigh_name},
                )
                neighborhoods[(city_name, neigh_name)] = neigh
                if created:
                    total_neigh += 1
        self.stdout.write(self.style.SUCCESS(f"  {total_neigh} quartiers crees"))

        # 3. Food categories
        self.stdout.write("Creation des categories alimentaires...")
        food_cats = {}
        for name, icon, order in FOOD_CATEGORIES_DATA:
            cat, _ = FoodCategory.objects.get_or_create(
                slug=slugify(name),
                defaults={"name": name, "icon": icon, "order": order},
            )
            food_cats[name] = cat
        self.stdout.write(self.style.SUCCESS(f"  {len(food_cats)} categories crees/existantes"))

        # 4. Demo owner user
        self.stdout.write("Creation de l'utilisateur proprietaire de demo...")
        owner, created = User.objects.get_or_create(
            username="demo_resto_owner",
            defaults={
                "email": "demo@eshelle-resto.cm",
                "first_name": "Propriétaire",
                "last_name": "Démo",
                "is_active": True,
            },
        )
        if created:
            owner.set_password("Demo@Resto2026")
            owner.save()
            self.stdout.write(self.style.SUCCESS("  Utilisateur demo cree: demo@eshelle-resto.cm / Demo@Resto2026"))
        else:
            self.stdout.write("  Utilisateur demo existant")

        # 5. Restaurants, menus, dishes
        self.stdout.write("Creation des restaurants et menus...")
        created_count = 0

        for resto_data in RESTAURANTS_DATA:
            city = cities[resto_data["city"]]
            neigh = neighborhoods.get((resto_data["city"], resto_data["neighborhood"]))

            # Create restaurant
            slug_base = slugify(resto_data["name"])
            slug = slug_base
            counter = 1
            while Restaurant.objects.filter(slug=slug).exists():
                slug = f"{slug_base}-{counter}"
                counter += 1

            restaurant, r_created = Restaurant.objects.get_or_create(
                name=resto_data["name"],
                owner=owner,
                defaults={
                    "slug": slug,
                    "description": resto_data["description"],
                    "city": city,
                    "neighborhood": neigh,
                    "address": resto_data["address"],
                    "phone": resto_data["phone"],
                    "whatsapp": resto_data["whatsapp"],
                    "status": resto_data["status"],
                    "opening_time": resto_data["opening_time"],
                    "closing_time": resto_data["closing_time"],
                    "is_approved": True,
                    "is_featured": resto_data.get("is_featured", False),
                    "is_active": True,
                    "views_count": __import__("random").randint(50, 500),
                },
            )

            if r_created:
                # Assign categories
                for cat_name in resto_data.get("categories", []):
                    if cat_name in food_cats:
                        restaurant.categories.add(food_cats[cat_name])

                # Create subscription (free trial)
                Subscription.objects.get_or_create(
                    restaurant=restaurant,
                    defaults={
                        "plan": "free_trial",
                        "is_active": True,
                        "expiry_date": date.today() + timedelta(days=30),
                    },
                )

                # Create menu categories and dishes
                menu_cats_map = {}
                for dish_data in resto_data.get("dishes", []):
                    cat_name = dish_data.get("category", "Plats principaux")
                    if cat_name not in menu_cats_map:
                        menu_cat, _ = MenuCategory.objects.get_or_create(
                            restaurant=restaurant,
                            name=cat_name,
                            defaults={"order": len(menu_cats_map)},
                        )
                        menu_cats_map[cat_name] = menu_cat
                    else:
                        menu_cat = menu_cats_map[cat_name]

                    Dish.objects.create(
                        restaurant=restaurant,
                        category=menu_cat,
                        name=dish_data["name"],
                        description=dish_data.get("description", ""),
                        price=dish_data["price"],
                        availability=dish_data.get("availability", "available"),
                        available_in_minutes=dish_data.get("available_in_minutes"),
                        is_popular=dish_data.get("is_popular", False),
                        is_active=True,
                    )

                created_count += 1
                self.stdout.write(f"  [OK] {restaurant.name} ({city.name}) - {len(resto_data['dishes'])} plats")
            else:
                self.stdout.write(f"  [skip] {restaurant.name} (deja existant)")

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Seed termine ! {created_count} restaurants crees avec leurs menus."
        ))
        self.stdout.write(self.style.SUCCESS(
            "   Compte demo : demo@eshelle-resto.cm / Demo@Resto2026"
        ))
        self.stdout.write(self.style.SUCCESS(
            "   Accedez a /resto/ pour voir les resultats."
        ))
