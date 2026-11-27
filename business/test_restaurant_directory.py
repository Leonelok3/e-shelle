from datetime import time, timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from resto.models import City, ContactLog, Dish, FoodCategory, Neighborhood, Restaurant, Subscription

from .models import BusinessCatalogItem, BusinessLeadEvent, BusinessProfile


class RestaurantDirectoryTests(TestCase):
    def setUp(self):
        self.url = reverse("restaurant_directory")
        self.owner = get_user_model().objects.create_user(
            username="directory-owner", email="directory-owner-private@example.com",
        )

    def business(self, name, city="Paris", **fields):
        return BusinessProfile.objects.create(
            owner=self.owner, module=BusinessProfile.Module.RESTO, name=name, city=city,
            **fields,
        )

    def resto(self, name, city, *, approved=True):
        restaurant = Restaurant.objects.create(
            owner=self.owner, name=name, city=city, address="Adresse de test",
            whatsapp="+237 680 62 50 82", phone="+237 699 00 00 00",
            opening_time=time(10), closing_time=time(22), is_approved=approved,
        )
        Subscription.objects.create(restaurant=restaurant, expiry_date=timezone.localdate() + timedelta(days=5))
        return restaurant

    def test_only_public_restaurants_appear_and_contact_uses_declared_number(self):
        visible = self.business("Table des Lumières", country="France", whatsapp="+33 612 345 678")
        self.business("Fiche privée unique", is_active=False)
        expired = self.business("Fiche expirée unique")
        BusinessProfile.objects.filter(pk=expired.pk).update(free_visibility_expires_at=timezone.now() - timedelta(days=1))
        self.business("Brouillon restaurant unique", activation_status=BusinessProfile.ActivationStatus.PENDING)
        no_whatsapp = self.business("Bistrot sans WhatsApp", phone="+33 644 111 222")
        legacy = self.resto("Cantine du Quartier", City.objects.create(name="Dakar"))
        hidden = self.resto("Restaurant refusé unique", legacy.city, approved=False)
        response = self.client.get(self.url)
        self.assertContains(response, visible.get_absolute_url())
        self.assertContains(response, reverse("resto:restaurant_detail", args=[legacy.slug]))
        self.assertEqual([card["name"] for card in response.context["cards"]].count(legacy.name), 1)
        for name in ("Fiche privée unique", "Fiche expirée unique", "Brouillon restaurant unique", hidden.name, self.owner.email, no_whatsapp.phone):
            self.assertNotContains(response, name)
        home = self.client.get(reverse("home"))
        self.assertContains(home, 'id="dir-preview-title"')
        self.assertContains(home, visible.name)
        self.assertNotContains(home, hidden.name)
        self.assertNotContains(home, "Fiche privée unique")

        detail = self.client.get(visible.get_absolute_url())
        self.assertContains(detail, "Voir tous les restaurants")
        self.assertContains(detail, "Écrire sur WhatsApp")
        self.assertNotContains(self.client.get(no_whatsapp.get_absolute_url()), no_whatsapp.phone)
        self.assertContains(self.client.get(reverse("resto:restaurant_detail", args=[legacy.slug])), "Voir tous les restaurants")

        client = Client(enforce_csrf_checks=True)
        client.get(self.url)
        token = client.cookies["csrftoken"].value
        contact = client.post(self.url, {"kind": "business", "restaurant_id": visible.pk}, HTTP_X_CSRFTOKEN=token)
        target = urlsplit(contact["Location"])
        self.assertEqual((target.netloc, target.path), ("wa.me", "/33612345678"))
        self.assertIn(visible.name, parse_qs(target.query)["text"][0])
        self.assertTrue(BusinessLeadEvent.objects.filter(business=visible, source="restaurant_directory", event_type="whatsapp").exists())
        self.assertEqual(client.post(self.url, {"kind": "resto", "restaurant_id": legacy.pk}, HTTP_X_CSRFTOKEN=token).status_code, 302)
        self.assertTrue(ContactLog.objects.filter(restaurant=legacy, action="whatsapp").exists())
        self.assertEqual(client.post(self.url, {"kind": "resto", "restaurant_id": hidden.pk}, HTTP_X_CSRFTOKEN=token).status_code, 404)
        self.assertEqual(client.post(self.url, {"kind": "business", "restaurant_id": no_whatsapp.pk}, HTTP_X_CSRFTOKEN=token).status_code, 404)
        sitemap = self.client.get(reverse("sitemap_xml"))
        self.assertContains(sitemap, self.url)
        self.assertContains(sitemap, reverse("resto:restaurant_detail", args=[legacy.slug]))
        self.assertNotContains(sitemap, reverse("resto:restaurant_detail", args=[hidden.slug]))

    def test_city_district_cuisine_search_boost_and_pagination(self):
        paris = City.objects.create(name="Paris")
        quartier = Neighborhood.objects.create(city=paris, name="Belleville")
        legacy = self.resto("Brasserie parisienne", paris)
        legacy.neighborhood = quartier
        legacy.save(update_fields=["neighborhood"])
        cuisine = FoodCategory.objects.create(name="Brasserie")
        legacy.categories.add(cuisine)
        Dish.objects.create(restaurant=legacy, name="Gratin maison", price=2000)
        boosted = self.business("Adresse en avant", district="Belleville", boost_expires_at=timezone.now() + timedelta(days=1))
        BusinessCatalogItem.objects.create(business=boosted, item_type=BusinessCatalogItem.ItemType.MENU, title="Gratin de saison", price_label="12 €")
        BusinessCatalogItem.objects.create(business=boosted, item_type=BusinessCatalogItem.ItemType.MENU, title="Plat privé unique", is_active=False)
        self.business("Autre quartier", district="Montmartre")
        self.business("Table hors ville", city="Montréal", district="Mile End")

        result = self.client.get(self.url, {"city": "paris", "district": "Belleville", "q": "gratin"})
        self.assertEqual([card["name"] for card in result.context["cards"]], [boosted.name, legacy.name])
        self.assertContains(result, "Restaurants à Paris")
        self.assertContains(result, "Mis en avant")
        self.assertContains(result, "12 €")
        self.assertNotContains(result, "Mile End")
        self.assertNotContains(result, "Plat privé unique")
        result = self.client.get(self.url, {"cuisine": cuisine.slug})
        self.assertEqual([card["name"] for card in result.context["cards"]], [legacy.name])

        for index in range(12):
            self.business(f"Table parisienne {index}")
        first = self.client.get(self.url, {"city": "Paris"})
        second = self.client.get(self.url, {"city": "Paris", "page": 2})
        self.assertEqual(len(first.context["cards"]), 12)
        self.assertEqual(len(second.context["cards"]), 3)
        self.assertTrue(first.context["next_url"].endswith("?city=Paris&page=2"))
        self.assertTrue(second.context["canonical"].endswith("?city=Paris&page=2"))

    def test_empty_results_and_home_hidden_below_three_public_restaurants(self):
        self.business("Une table publique")
        self.business("Une table non publiée", is_active=False)
        empty = self.client.get(self.url, {"city": "Introuvable"})
        self.assertContains(empty, "Aucun restaurant ne correspond")
        self.assertContains(empty, reverse("business:onboarding") + "?plan=free")
        self.assertNotContains(self.client.get(reverse("home")), 'id="dir-preview-title"')
