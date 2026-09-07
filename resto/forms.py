"""
E-Shelle Resto — Formulaires
"""
from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Restaurant, Dish, MenuCategory, City, Neighborhood, FoodCategory, Review


class RestaurantForm(forms.ModelForm):
    """Formulaire d'édition du profil restaurant (dashboard)."""

    neighborhood_name = forms.CharField(
        max_length=120, required=False, label="Quartier",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Makepe, Bonamoussadi, Ndokoti..."}),
    )

    class Meta:
        model = Restaurant
        fields = [
            "name", "description", "cover_image", "logo",
            "city", "address", "phone", "whatsapp",
            "categories", "opening_time", "closing_time", "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nom du restaurant"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 3, "placeholder": "Décrivez votre restaurant..."}),
            "address": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Rue de la Réunification, Bastos"}),
            "phone": forms.TextInput(attrs={"class": "form-input", "placeholder": "+237 6XX XX XX XX"}),
            "whatsapp": forms.TextInput(attrs={"class": "form-input", "placeholder": "+237 6XX XX XX XX"}),
            "opening_time": forms.TimeInput(attrs={"class": "form-input", "type": "time"}),
            "closing_time": forms.TimeInput(attrs={"class": "form-input", "type": "time"}),
            "status": forms.Select(attrs={"class": "form-input"}),
            "city": forms.Select(attrs={"class": "form-input"}),
            "categories": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.neighborhood_id:
            self.fields["neighborhood_name"].initial = self.instance.neighborhood.name

    def save(self, commit=True):
        restaurant = super().save(commit=False)
        name = (self.cleaned_data.get("neighborhood_name") or "").strip()
        city = self.cleaned_data.get("city")
        if name and city:
            neighborhood, _ = Neighborhood.objects.get_or_create(
                city=city, slug=slugify(name),
                defaults={"name": name},
            )
            restaurant.neighborhood = neighborhood
        else:
            restaurant.neighborhood = None
        if commit:
            restaurant.save()
            self.save_m2m()
        return restaurant

    def clean_cover_image(self):
        image = self.cleaned_data.get("cover_image")
        # image.content_type n'existe que sur un fichier fraichement televerse
        # (UploadedFile). Si le champ n'est pas modifie, Django repasse le
        # ImageFieldFile deja enregistre, qui n'a pas cet attribut.
        if image and hasattr(image, "content_type"):
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("L'image ne doit pas dépasser 5 Mo.")
            if image.content_type not in ["image/jpeg", "image/png", "image/webp"]:
                raise ValidationError("Format accepté : JPG, PNG ou WebP.")
        return image

    def clean_logo(self):
        logo = self.cleaned_data.get("logo")
        if logo and hasattr(logo, "size"):
            if logo.size > 2 * 1024 * 1024:
                raise ValidationError("Le logo ne doit pas dépasser 2 Mo.")
        return logo

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if phone and not phone.startswith("+237"):
            raise ValidationError("Le numéro doit commencer par +237.")
        return phone

    def clean_whatsapp(self):
        wa = self.cleaned_data.get("whatsapp", "").strip()
        if wa and not wa.startswith("+237"):
            raise ValidationError("Le numéro WhatsApp doit commencer par +237.")
        return wa


class DishForm(forms.ModelForm):
    """Formulaire d'ajout/édition d'un plat."""

    class Meta:
        model = Dish
        fields = [
            "name", "description", "price", "image",
            "category", "availability", "available_in_minutes",
            "is_popular", "order",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Nom du plat"}),
            "description": forms.Textarea(attrs={"class": "form-input", "rows": 2, "placeholder": "Description courte..."}),
            "price": forms.NumberInput(attrs={"class": "form-input", "placeholder": "Ex: 2500", "min": "0"}),
            "category": forms.Select(attrs={"class": "form-input"}),
            "availability": forms.Select(attrs={"class": "form-input"}),
            "available_in_minutes": forms.NumberInput(attrs={"class": "form-input", "placeholder": "Ex: 15", "min": "1"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
        }

    def __init__(self, *args, restaurant=None, **kwargs):
        super().__init__(*args, **kwargs)
        if restaurant:
            self.fields["category"].queryset = MenuCategory.objects.filter(restaurant=restaurant)

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is not None and price < 0:
            raise ValidationError("Le prix ne peut pas être négatif.")
        return price

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and hasattr(image, "size"):
            if image.size > 5 * 1024 * 1024:
                raise ValidationError("L'image ne doit pas dépasser 5 Mo.")
        return image


class DishAvailabilityForm(forms.ModelForm):
    """Formulaire rapide pour changer la disponibilité d'un plat (HTMX)."""

    class Meta:
        model = Dish
        fields = ["availability", "available_in_minutes"]


class MenuCategoryForm(forms.ModelForm):
    """Formulaire de catégorie de menu."""

    class Meta:
        model = MenuCategory
        fields = ["name", "order"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input", "placeholder": "Ex: Plats principaux"}),
            "order": forms.NumberInput(attrs={"class": "form-input", "min": "0"}),
        }


class RestaurantRegisterForm(forms.Form):
    """Formulaire d'inscription restaurant (crée user + restaurant)."""

    # User fields
    first_name = forms.CharField(
        max_length=100, label="Prénom",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Votre prénom"})
    )
    last_name = forms.CharField(
        max_length=100, label="Nom",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Votre nom"})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"class": "form-input", "placeholder": "votre@email.com"})
    )
    password = forms.CharField(
        label="Mot de passe",
        widget=forms.PasswordInput(attrs={"class": "form-input", "placeholder": "Minimum 8 caractères"}),
        min_length=8,
    )

    # Restaurant fields
    restaurant_name = forms.CharField(
        max_length=200, label="Nom du restaurant",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Chez Mama Fouda"})
    )
    city = forms.ModelChoiceField(
        queryset=City.objects.filter(is_active=True),
        label="Ville",
        widget=forms.Select(attrs={"class": "form-input"}),
    )
    phone = forms.CharField(
        max_length=20, label="Téléphone",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+237 6XX XX XX XX"})
    )
    whatsapp = forms.CharField(
        max_length=20, label="WhatsApp",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "+237 6XX XX XX XX"})
    )
    address = forms.CharField(
        max_length=300, label="Adresse",
        widget=forms.TextInput(attrs={"class": "form-input", "placeholder": "Quartier, rue..."})
    )
    opening_time = forms.TimeField(
        label="Heure d'ouverture",
        widget=forms.TimeInput(attrs={"class": "form-input", "type": "time"})
    )
    closing_time = forms.TimeField(
        label="Heure de fermeture",
        widget=forms.TimeInput(attrs={"class": "form-input", "type": "time"})
    )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone", "").strip()
        if not phone.startswith("+237"):
            raise ValidationError("Le numéro doit commencer par +237.")
        return phone

    def clean_whatsapp(self):
        wa = self.cleaned_data.get("whatsapp", "").strip()
        if not wa.startswith("+237"):
            raise ValidationError("Le numéro WhatsApp doit commencer par +237.")
        return wa


class ReviewForm(forms.ModelForm):
    """Formulaire d'avis client — affiché sur la page restaurant."""

    class Meta:
        model = Review
        fields = ["author_name", "rating", "comment"]
        widgets = {
            "author_name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Votre prénom (ex: Marie, Jean…)",
            }),
            "rating": forms.HiddenInput(attrs={"id": "rating-value"}),
            "comment": forms.Textarea(attrs={
                "class": "form-input",
                "rows": 3,
                "placeholder": "Partagez votre expérience…",
                "maxlength": "800",
            }),
        }

    def clean_comment(self):
        comment = self.cleaned_data.get("comment", "").strip()
        if len(comment) < 10:
            raise ValidationError("Votre avis doit contenir au moins 10 caractères.")
        return comment

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if not rating or int(rating) not in range(1, 6):
            raise ValidationError("Veuillez choisir une note entre 1 et 5 étoiles.")
        return rating
