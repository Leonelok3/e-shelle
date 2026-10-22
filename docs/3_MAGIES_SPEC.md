# Les 3 expériences commerce E-Shelle / E-Shelle’s 3 commerce experiences

## Français

### 1. Message vocal produit dans la langue du business

Le profil Business peut choisir le français, l’anglais, le Pidgin camerounais, l’Ewondo ou le Bassa. `send_vocal_campaign` prépare un script à partir du produit, de son prix et du stock, crée un `VoiceOverJob`, puis envoie le fichier audio par le WABA de l’entreprise. Chaque destinataire est contrôlé au moment de l’envoi : il doit appartenir à la PME et avoir encore son consentement marketing. L’historique privé WhatsApp enregistre le type `audio` et la langue.

Les scripts français, anglais et Pidgin ont des variantes locales définies dans le code. Ewondo et Bassa passent par une traduction E-Shelle AI et doivent être relus par un locuteur avant une utilisation commerciale. La qualité de prononciation dépend du fournisseur vocal et n’est pas garantie. Aucun gain de conversion n’est revendiqué sans mesure.

### 2. Photo vers produit catalogue

Le propriétaire d’une fiche peut envoyer une photo depuis le catalogue. Phone OCR Agent extrait localement le texte; E-Shelle AI le structure en SKU, nom français/anglais, prix détail, prix gros, stock et catégorie. Les prix doivent être positifs et le stock nul ou positif. Le produit est créé ou mis à jour par SKU et l’image est conservée avec le stockage configuré pour `BusinessCatalogItem.image` (Cloudinary dans l’environnement prévu). Les produits absents ne sont jamais supprimés.

L’analyse dépend de Tesseract pour l’OCR et d’une clé E-Shelle AI configurée. Les valeurs incertaines ou absentes sont refusées au lieu d’être inventées. Le propriétaire doit vérifier le résultat avant de vendre.

### 3. Achat groupé Njangi

`NjangiAchatGroupe` suit l’objectif de quantité, les prix, la date de clôture, les invitations et les participations de boutiques. `lancer_njangi_achat` cible les quincailleries situées à Akwa, ne contacte que des contacts marketing consentants via leur WABA et ne tente un texte libre que dans la fenêtre WhatsApp de 24 heures. Le contact peut répondre `OUI` (ou `OUI <quantité>`); l’inbox rattache cette réponse à l’invitation de sa propre entreprise, met à jour la participation et plafonne le cumul à la quantité cible.

Hors de la fenêtre de 24 heures, l’invitation est ignorée : un modèle marketing approuvé et adapté devra être configuré pour ce parcours avant d’élargir l’envoi. Les statuts « commandé » et « livré » restent des étapes manuelles. Le badge « Lancer en Njangi » sur le catalogue signale les articles dont le stock dépasse 50 unités.

## English

### 1. Product voice message in the business language

Business profiles can choose French, English, Cameroonian Pidgin, Ewondo, or Bassa. `send_vocal_campaign` builds a script from product, price, and stock data, creates a `VoiceOverJob`, and sends the audio through that business’s WABA. Each recipient is checked at send time: the contact must belong to the business and still have marketing consent. The private WhatsApp history records the `audio` type and language.

French, English, and Pidgin scripts have code-defined variants. Ewondo and Bassa use E-Shelle AI translation and should be reviewed by a native speaker before commercial use. Pronunciation quality depends on the voice provider and is not guaranteed. No conversion lift is claimed without measurement.

### 2. Photo to catalogue product

The owner of a business profile can submit a product photo from the catalogue page. Phone OCR Agent extracts text locally; E-Shelle AI structures it into SKU, French/English names, retail and wholesale prices, stock, and category. Prices must be positive and stock must be zero or greater. The product is created or updated by SKU, and its image is stored through the configured `BusinessCatalogItem.image` storage (Cloudinary in the intended deployment). Products missing from an import are never deleted.

The flow requires Tesseract for OCR and a configured E-Shelle AI key. Missing or invalid values are rejected instead of invented. The owner should review the result before selling.

### 3. Njangi group buying

`NjangiAchatGroupe` tracks the quantity target, prices, closing time, invitations, and shop participation. `lancer_njangi_achat` targets hardware shops in Akwa, contacts only marketing-consented contacts through their own WABA, and sends free-form text only inside WhatsApp’s 24-hour window. A contact can reply `OUI` (or `OUI <quantity>`); the inbox associates the reply with an invitation for that contact’s business, updates participation, and caps the total at the target quantity.

Invitations outside the 24-hour window are skipped. A suitable approved marketing template must be configured before expanding those sends. “Ordered” and “delivered” remain manual statuses. The “Lancer en Njangi” catalogue badge marks products with stock above 50 units.

## Vérification / Verification

- `whatsapp_agent.tests_business_campaigns`: 27 passed.
- `business.tests_catalog_import`: 6 passed, including photo-to-product and the ten-product CSV sample.
- `whatsapp_commerce.tests`: 40 passed, including Pidgin audio delivery and Njangi group target completion.
- Combined: 73 passed. Local test runs set `PYTHON_DOTENV_DISABLED=1` and `SECURE_SSL_REDIRECT=false`; no `.env` values were read or printed.
