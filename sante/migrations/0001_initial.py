# Generated manually for E-Shelle Santé.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="CategorieSante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=120)),
                ("slug", models.SlugField(blank=True, max_length=140, unique=True)),
                ("type_categorie", models.CharField(choices=[("SERVICE", "Service"), ("PRODUIT", "Produit"), ("SPECIALITE", "Spécialité")], default="PRODUIT", max_length=20)),
                ("icone", models.CharField(default="+", max_length=10)),
                ("description", models.CharField(blank=True, max_length=220)),
                ("ordre", models.PositiveIntegerField(default=0)),
                ("active", models.BooleanField(default=True)),
            ],
            options={
                "verbose_name": "Catégorie santé",
                "verbose_name_plural": "Catégories santé",
                "ordering": ["ordre", "nom"],
            },
        ),
        migrations.CreateModel(
            name="VilleSante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=80)),
                ("slug", models.SlugField(blank=True, max_length=100, unique=True)),
                ("region", models.CharField(blank=True, max_length=80)),
                ("active", models.BooleanField(default=True)),
                ("ordre", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Ville",
                "verbose_name_plural": "Villes",
                "ordering": ["ordre", "nom"],
            },
        ),
        migrations.CreateModel(
            name="DemandeSante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=120)),
                ("telephone", models.CharField(max_length=30)),
                ("besoin", models.CharField(max_length=180)),
                ("message", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("ville", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="demandes", to="sante.villesante")),
            ],
            options={
                "verbose_name": "Demande santé",
                "verbose_name_plural": "Demandes santé",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ProfessionnelSante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nom", models.CharField(max_length=160)),
                ("slug", models.SlugField(blank=True, max_length=200, unique=True)),
                ("type_pro", models.CharField(choices=[("MEDECIN", "Médecin"), ("CLINIQUE", "Clinique"), ("INFIRMIER", "Infirmier"), ("LABO", "Laboratoire"), ("KINE", "Kinésithérapeute"), ("BIEN_ETRE", "Bien-être")], default="CLINIQUE", max_length=20)),
                ("quartier", models.CharField(blank=True, max_length=120)),
                ("adresse", models.CharField(blank=True, max_length=240)),
                ("description", models.TextField(blank=True)),
                ("telephone", models.CharField(max_length=30)),
                ("whatsapp", models.CharField(blank=True, help_text="Numéro WhatsApp sans +", max_length=30)),
                ("horaires", models.CharField(default="Lun-Sam 8h-18h", max_length=180)),
                ("consultation_domicile", models.BooleanField(default=False)),
                ("urgence", models.BooleanField(default=False)),
                ("teleconsultation", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("is_featured", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("auteur", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="profils_sante", to=settings.AUTH_USER_MODEL)),
                ("specialites", models.ManyToManyField(blank=True, related_name="professionnels", to="sante.categoriesante")),
                ("ville", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="professionnels", to="sante.villesante")),
            ],
            options={
                "verbose_name": "Professionnel santé",
                "verbose_name_plural": "Professionnels santé",
                "ordering": ["-is_featured", "-is_verified", "nom"],
            },
        ),
        migrations.CreateModel(
            name="ProduitSante",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("titre", models.CharField(max_length=180)),
                ("slug", models.SlugField(blank=True, max_length=220, unique=True)),
                ("type_produit", models.CharField(choices=[("BIEN_ETRE", "Bien-être"), ("COMPLEMENT", "Complément"), ("HYGIENE", "Hygiène"), ("MATERIEL", "Matériel médical"), ("BEBE", "Bébé & maman"), ("SPORT", "Sport santé")], default="BIEN_ETRE", max_length=20)),
                ("description", models.TextField()),
                ("image", models.ImageField(blank=True, null=True, upload_to="sante/produits/")),
                ("vendeur_nom", models.CharField(max_length=140)),
                ("telephone", models.CharField(max_length=30)),
                ("whatsapp", models.CharField(blank=True, help_text="Numéro WhatsApp sans +", max_length=30)),
                ("prix", models.PositiveIntegerField(default=0)),
                ("prix_barre", models.PositiveIntegerField(blank=True, null=True)),
                ("stock_disponible", models.PositiveIntegerField(default=1)),
                ("livraison", models.BooleanField(default=False)),
                ("ordonnance_requise", models.BooleanField(default=False)),
                ("is_active", models.BooleanField(default=False)),
                ("is_verified", models.BooleanField(default=False)),
                ("is_featured", models.BooleanField(default=False)),
                ("vues", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("auteur", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="produits_sante", to=settings.AUTH_USER_MODEL)),
                ("categorie", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="produits", to="sante.categoriesante")),
                ("ville", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="produits", to="sante.villesante")),
            ],
            options={
                "verbose_name": "Produit santé",
                "verbose_name_plural": "Produits santé",
                "ordering": ["-is_featured", "-created_at"],
                "indexes": [
                    models.Index(fields=["is_active", "is_verified", "created_at"], name="sante_produ_is_acti_5563c2_idx"),
                    models.Index(fields=["ville", "type_produit"], name="sante_produ_ville_i_955369_idx"),
                ],
            },
        ),
    ]
