# Agent LEBELAGE et export Shopify local

Cet agent sert d'abord a travailler proprement en local:

1. exporter les produits LEBELAGE dans des fichiers locaux;
2. exporter les produits deja presents dans ta boutique Shopify dans des fichiers locaux;
3. verifier et comparer avant toute importation.

Interface locale:

```text
http://127.0.0.1:8000/lebelage-importer/
```

## Test local sans Shopify

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --limit 10 --max-pages 1
```

Resultats generes:

- `tmp/lebelage_products.json`
- `tmp/lebelage_products.csv`

Ce mode ne touche pas a Shopify. Il sert a verifier les noms, prix, images, descriptions et URLs source.

Pour appliquer livraison et marge:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --limit 10 --max-pages 1 --shipping 5 --margin 10
```

Le fichier local contient alors:

- `final_price_amount`;
- `selling_description`.

## Export local des produits Shopify

Creer une app Shopify Admin dans la boutique, puis donner au token les scopes:

- `read_products`

Variables d'environnement attendues:

```powershell
$env:SHOPIFY_SHOP_DOMAIN="ma-boutique.myshopify.com"
$env:SHOPIFY_ADMIN_ACCESS_TOKEN="shpat_xxxxxxxxx"
$env:SHOPIFY_API_VERSION="2026-01"
```

Le script accepte aussi les variables deja utilisees dans E-Shelle:

```powershell
$env:TIBO_SHOPIFY_SHOP_DOMAIN="ma-boutique.myshopify.com"
$env:TIBO_SHOPIFY_ACCESS_TOKEN="shpat_xxxxxxxxx"
$env:TIBO_SHOPIFY_API_VERSION="2026-01"
```

Commande d'export de ta boutique Shopify vers fichiers locaux:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --export-shopify
```

Resultats generes:

- `tmp/shopify_products.json`
- `tmp/shopify_products.csv`

## Comparer LEBELAGE et Shopify

Depuis l'interface:

```text
http://127.0.0.1:8000/lebelage-importer/
```

Cliquer sur:

```text
Comparer LEBELAGE vs Shopify
```

Resultats generes:

- `tmp/lebelage_shopify_comparison.json`
- `tmp/lebelage_shopify_comparison.csv`

Le comparateur montre:

- nouveaux produits;
- doublons possibles;
- prix differents.

Depuis le terminal:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --limit 10 --max-pages 1 --compare
```

## Import Shopify plus tard

Quand tu auras verifie les deux exports locaux, l'import peut etre lance en ligne de commande. Pour importer, il faudra aussi le scope:

- `write_products`

Commande d'import:

```powershell
.\.venv\Scripts\python.exe tools\lebelage_shopify_agent.py --limit 10 --max-pages 1 --import-shopify
```

L'import cree les produits en brouillon Shopify (`draft`) par defaut pour eviter une publication directe.

Dans l'interface, il faut taper:

```text
BROUILLON
```

puis cliquer sur:

```text
Importer en brouillon
```

## Guide PDF

Guide genere:

```text
docs/guide_utilisation_lebelage_shopify.pdf
```

Pour regenerer le PDF:

```powershell
.\.venv\Scripts\python.exe docs\generate_guide_lebelage_shopify_pdf.py
```

## Strategie technique

- Scraping local avec `requests` et `HTMLParser`, sans dependance lourde.
- Detection des pages categorie et produits via les liens contenant `/product/`.
- Pagination par ajout ou remplacement de `page=N`.
- Arret automatique quand aucune nouvelle URL produit n'est trouvee.
- Export JSON/CSV avant import pour controle humain.
- Creation Shopify REST Admin API avec titre, prix, description HTML, image, tags, SKU et source URL.

Si le site change et charge les produits uniquement en JavaScript, il faudra passer a Playwright ou Selenium. Pour l'instant, le HTML renvoie bien les produits.

## Champs Shopify principaux

Minimum utile pour creer un produit:

- `title`
- `variants.price`

Champs ajoutes par l'agent:

- `body_html`
- `vendor = LEBELAGE`
- `product_type = Skincare`
- `tags = hypoallergenic, LEBELAGE, k-beauty, imported`
- `images.src`
- `variants.sku`
- `metafields.source.lebelage_url`

## Strategie de mise a jour

L'agent cherche d'abord un produit existant par titre exact. Pour une production plus stricte, la meilleure evolution est de chercher par SKU ou par metafield `source.lebelage_url`, car le titre peut changer.

## Attention business

Avant d'importer et vendre les produits, verifier:

- droit de revente ou partenariat fournisseur;
- autorisation d'utiliser les images;
- marge, livraison, taxes et retours;
- conformite cosmetique du pays de vente.
