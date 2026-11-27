from django.conf import settings
from django.db import models
from django.utils import timezone
import uuid


class BusinessWhatsAppConnection(models.Model):
	"""A WhatsApp Business account connected to one E-Shelle business profile."""

	class Status(models.TextChoices):
		CONNECTING = "connecting", "Connexion en cours"
		ACTIVE = "active", "Connecte"
		ACTION_REQUIRED = "action_required", "Action requise"
		DISCONNECTED = "disconnected", "Deconnecte"

	business = models.OneToOneField(
		"business.BusinessProfile",
		on_delete=models.CASCADE,
		related_name="whatsapp_connection",
	)
	waba_id = models.CharField(max_length=64, unique=True)
	phone_number_id = models.CharField(max_length=64, unique=True)
	meta_business_id = models.CharField(max_length=64, blank=True)
	catalog_id = models.CharField(max_length=64, blank=True)
	display_phone_number = models.CharField(max_length=32, blank=True)
	access_token_encrypted = models.TextField(blank=True)
	phone_registered = models.BooleanField(default=False)
	webhook_subscribed = models.BooleanField(default=False)
	status = models.CharField(max_length=24, choices=Status.choices, default=Status.CONNECTING)
	agent_enabled = models.BooleanField(default=False)
	automations_enabled = models.BooleanField(default=False)
	agent_tone = models.CharField(
		max_length=16,
		choices=[
			("professional", "Professionnel"),
			("friendly", "Familier"),
			("pidgin", "Pidgin"),
		],
		default="friendly",
	)
	agent_catalog_items = models.ManyToManyField(
		"business.BusinessCatalogItem",
		blank=True,
		related_name="whatsapp_agent_connections",
	)
	last_error = models.CharField(max_length=500, blank=True)
	meta_phone_status = models.CharField(max_length=32, blank=True)
	meta_verified_name = models.CharField(max_length=180, blank=True)
	meta_quality_rating = models.CharField(max_length=32, blank=True)
	meta_messaging_limit = models.CharField(max_length=64, blank=True)
	last_meta_sync_at = models.DateTimeField(null=True, blank=True)
	connected_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["business_id"]
		verbose_name = "Connexion WhatsApp Business"
		verbose_name_plural = "Connexions WhatsApp Business"

	def set_access_token(self, token):
		from .security import encrypt_access_token

		self.access_token_encrypted = encrypt_access_token(token)

	def get_access_token(self):
		from .security import decrypt_access_token

		return decrypt_access_token(self.access_token_encrypted)


class BusinessWhatsAppActivation(models.Model):
	connection = models.OneToOneField(
		BusinessWhatsAppConnection, on_delete=models.CASCADE, related_name="activation",
	)
	opening_hours = models.CharField(max_length=500, blank=True)
	answer_hours = models.BooleanField(default=True)
	answer_catalog = models.BooleanField(default=False)
	assist_sales = models.BooleanField(default=False)
	voice_enabled = models.BooleanField(default=False)
	booking_service = models.ForeignKey(
		"salonhub_salons.Service", null=True, blank=True, on_delete=models.SET_NULL,
	)
	activated_at = models.DateTimeField(null=True, blank=True)
	test_code = models.CharField(max_length=16, blank=True)
	test_sender = models.CharField(max_length=20, blank=True)
	test_phone_number_id = models.CharField(max_length=64, blank=True)
	test_expires_at = models.DateTimeField(null=True, blank=True)
	test_message = models.ForeignKey(
		"BusinessWhatsAppMessage", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
	)
	test_reply = models.ForeignKey(
		"BusinessWhatsAppMessage", null=True, blank=True, on_delete=models.SET_NULL, related_name="+",
	)


class WhatsAppCatalogSender(models.Model):
	business = models.OneToOneField(
		"business.BusinessProfile", on_delete=models.CASCADE, related_name="whatsapp_catalog_sender",
	)
	owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
	requested_phone = models.CharField(max_length=20, blank=True)
	pairing_digest = models.CharField(max_length=64, blank=True, db_index=True)
	pairing_expires_at = models.DateTimeField(null=True, blank=True)
	auto_publish = models.BooleanField(default=False)


class WhatsAppCatalogSubmission(models.Model):
	class Status(models.TextChoices):
		PENDING = "pending", "En attente de traitement"
		PROCESSING = "processing", "Analyse en cours"
		REVIEW = "review", "À valider"
		PUBLISHED = "published", "Publié"
		REJECTED = "rejected", "Écarté"
		ATTACHED = "attached", "Photo rattachée"

	sender = models.ForeignKey(WhatsAppCatalogSender, on_delete=models.CASCADE, related_name="submissions")
	owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
	sender_phone = models.CharField(max_length=20)
	wa_message_id = models.CharField(max_length=200, unique=True)
	body = models.TextField(blank=True)
	media_id = models.CharField(max_length=80, blank=True)
	private_image = models.CharField(max_length=255, blank=True)
	title = models.CharField(max_length=140, blank=True)
	price_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
	currency = models.CharField(max_length=3, blank=True)
	sku = models.CharField(max_length=80, blank=True)
	stock = models.PositiveIntegerField(null=True, blank=True)
	reason = models.CharField(max_length=245, blank=True)
	item = models.ForeignKey("business.BusinessCatalogItem", null=True, blank=True, on_delete=models.SET_NULL)
	attached_to = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="attached_photos")
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
	dispatch_after = models.DateTimeField(default=timezone.now)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["-created_at", "-pk"]
		indexes = [
			models.Index(fields=["status", "dispatch_after"], name="wa_cat_due_idx"),
			models.Index(fields=["status", "updated_at"], name="wa_cat_state_idx"),
		]

	@property
	def can_attach_photo(self):
		return self.status == self.Status.REVIEW and bool(self.private_image) and not self.body.strip()


class WhatsAppProviderReferral(models.Model):
	class Status(models.TextChoices):
		CLICKED = "clicked", "Lien ouvert"
		ONBOARDING = "onboarding", "Connexion commencée"
		CONNECTED = "connected", "WABA connectée"
		FAILED = "failed", "Connexion à reprendre"

	source = models.CharField(max_length=80, default="whatsapp_business_sales_page")
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.CLICKED, db_index=True)
	business = models.ForeignKey(
		"business.BusinessProfile",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="whatsapp_provider_referrals",
	)
	connection = models.ForeignKey(
		"whatsapp_commerce.BusinessWhatsAppConnection",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="provider_referrals",
	)
	clicked_at = models.DateTimeField(auto_now_add=True)
	signup_started_at = models.DateTimeField(null=True, blank=True)
	connected_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		ordering = ["-clicked_at", "-pk"]
		indexes = [
			models.Index(fields=["status", "clicked_at"]),
			models.Index(fields=["business", "status"]),
		]


class BusinessWhatsAppContact(models.Model):
	"""Private CRM contact; the same phone may belong to different businesses."""

	class PipelineStatus(models.TextChoices):
		NEW = "new", "Nouveau"
		OPEN = "open", "À traiter"
		QUALIFIED = "qualified", "Qualifié"
		WON = "won", "Gagné"
		LOST = "lost", "Perdu"

	business = models.ForeignKey(
		"business.BusinessProfile",
		on_delete=models.CASCADE,
		related_name="whatsapp_contacts",
	)
	phone = models.CharField(max_length=20)
	display_name = models.CharField(max_length=180, blank=True)
	marketing_opt_in = models.BooleanField(default=False)
	consent_service = models.BooleanField(default=False)
	consent_marketing = models.BooleanField(default=False)
	consent_source = models.CharField(max_length=120, blank=True)
	consented_at = models.DateTimeField(null=True, blank=True)
	consent_recorded_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="recorded_whatsapp_consents",
	)
	opted_out_at = models.DateTimeField(null=True, blank=True)
	agent_paused = models.BooleanField(default=False)
	last_inbound_at = models.DateTimeField(null=True, blank=True, db_index=True)
	pipeline_status = models.CharField(
		max_length=16,
		choices=PipelineStatus.choices,
		default=PipelineStatus.NEW,
		db_index=True,
	)
	tags = models.JSONField(default=list, blank=True)
	custom_fields = models.JSONField(default=dict, blank=True)
	property_filters = models.JSONField(default=dict, blank=True)
	selected_property = models.ForeignKey(
		"immobilier_cameroun.Bien", null=True, blank=True, on_delete=models.SET_NULL,
	)
	notes = models.TextField(blank=True)
	next_follow_up_at = models.DateField(null=True, blank=True, db_index=True)
	last_activity_at = models.DateTimeField(auto_now=True, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["business", "phone"],
				name="wa_biz_contact_phone_uniq",
			),
		]
		ordering = ["-last_activity_at", "-pk"]
		indexes = [
			models.Index(fields=["business", "last_activity_at"]),
			models.Index(fields=["business", "pipeline_status", "next_follow_up_at"]),
		]
		verbose_name = "Contact WhatsApp business"
		verbose_name_plural = "Contacts WhatsApp business"

	def __str__(self):
		return self.display_name or self.phone


class BusinessWhatsAppMessage(models.Model):
	"""Minimal message history for the business-owned WhatsApp inbox."""

	class Direction(models.TextChoices):
		INBOUND = "inbound", "Entrant"
		OUTBOUND = "outbound", "Sortant"

	contact = models.ForeignKey(
		BusinessWhatsAppContact,
		on_delete=models.CASCADE,
		related_name="messages",
	)
	wa_message_id = models.CharField(max_length=200, unique=True)
	is_activation_test = models.BooleanField(default=False)
	direction = models.CharField(max_length=12, choices=Direction.choices)
	message_type = models.CharField(max_length=32, default="text")
	media_id = models.CharField(max_length=80, blank=True)
	language = models.CharField(max_length=16, blank=True)
	body = models.TextField(blank=True)
	status = models.CharField(max_length=24, blank=True)
	meta_timestamp = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ["created_at", "pk"]
		verbose_name = "Message WhatsApp business"
		verbose_name_plural = "Messages WhatsApp business"

	def __str__(self):
		return f"{self.contact.phone} - {self.direction}"


class BusinessWhatsAppReplyJob(models.Model):
	"""Pending automatic reply for a single persisted incoming message."""

	class Status(models.TextChoices):
		PENDING = "pending", "Réponse en attente"
		PROCESSING = "processing", "Réponse en cours"
		SENT = "sent", "Réponse envoyée"
		SKIPPED = "skipped", "Réponse automatique ignorée"
		REVIEW = "review", "Intervention de l’équipe"

	class BookingHelp(models.TextChoices):
		NO_SLOTS = "no_slots", "Aucun créneau disponible"
		UNSUITABLE = "unsuitable", "Le client demande un autre créneau"
		SLOT_TAKEN = "slot_taken", "Le créneau demandé est indisponible"
		NO_AGENDA = "no_agenda", "L’équipe doit proposer un créneau"

	message = models.OneToOneField(
		BusinessWhatsAppMessage, on_delete=models.CASCADE, related_name="reply_job",
	)
	connection = models.ForeignKey(BusinessWhatsAppConnection, on_delete=models.CASCADE)
	phone_number_id = models.CharField(max_length=64)
	activation_code = models.CharField(max_length=16, blank=True)
	status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
	booking_help = models.CharField(max_length=16, choices=BookingHelp.choices, blank=True, default="")
	follow_up_item = models.ForeignKey("business.BusinessCatalogItem", null=True, blank=True, on_delete=models.SET_NULL)
	follow_up_order = models.ForeignKey("WhatsAppDraftOrder", null=True, blank=True, on_delete=models.SET_NULL)
	follow_up_property = models.ForeignKey("immobilier_cameroun.Bien", null=True, blank=True, on_delete=models.SET_NULL)
	follow_up_service = models.ForeignKey("salonhub_salons.Service", null=True, blank=True, on_delete=models.SET_NULL)
	follow_up_appointment = models.ForeignKey("salonhub_bookings.Appointment", null=True, blank=True, on_delete=models.SET_NULL)
	follow_up_closed_at = models.DateTimeField(null=True, blank=True)
	automation_message = models.ForeignKey("ScheduledBusinessWhatsAppMessage", null=True, blank=True, on_delete=models.SET_NULL)
	automation_action = models.CharField(max_length=16, blank=True)
	dispatch_after = models.DateTimeField(default=timezone.now)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		indexes = [
			models.Index(fields=["status", "dispatch_after"], name="wa_reply_due_idx"),
			models.Index(fields=["status", "updated_at"], name="wa_reply_state_idx"),
		]


class BusinessWhatsAppAudit(models.Model):
	"""Tenant-scoped record of automated WhatsApp decisions and Meta events."""

	connection = models.ForeignKey(
		BusinessWhatsAppConnection,
		on_delete=models.CASCADE,
		related_name="audit_events",
	)
	contact = models.ForeignKey(
		BusinessWhatsAppContact,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="audit_events",
	)
	event_type = models.CharField(max_length=48, db_index=True)
	intent = models.CharField(max_length=32, blank=True)
	action = models.CharField(max_length=64, blank=True)
	details = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ["-created_at", "-pk"]
		indexes = [models.Index(fields=["connection", "event_type", "created_at"])]


class WhatsAppOfferClick(models.Model):
	reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	connection = models.ForeignKey(BusinessWhatsAppConnection, on_delete=models.CASCADE)
	phone_number_id = models.CharField(max_length=64)
	catalog_item = models.ForeignKey("business.BusinessCatalogItem", null=True, blank=True, on_delete=models.CASCADE)
	property_listing = models.ForeignKey("immobilier_cameroun.Bien", null=True, blank=True, on_delete=models.CASCADE)
	entry_message = models.OneToOneField(BusinessWhatsAppMessage, null=True, blank=True, on_delete=models.SET_NULL)
	campaign = models.ForeignKey("whatsapp_agent.Campagne", null=True, blank=True, on_delete=models.SET_NULL)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		constraints = [models.CheckConstraint(
			condition=(models.Q(catalog_item__isnull=False, property_listing__isnull=True)
			           | models.Q(catalog_item__isnull=True, property_listing__isnull=False)),
			name="wa_offer_click_exactly_one_offer",
		)]


class BusinessWhatsAppBooking(models.Model):
	appointment = models.OneToOneField("salonhub_bookings.Appointment", on_delete=models.CASCADE)
	contact = models.ForeignKey(BusinessWhatsAppContact, on_delete=models.CASCADE)
	property_visit = models.OneToOneField(
		"immobilier_cameroun.DemandeVisite", null=True, blank=True, on_delete=models.SET_NULL,
	)
	source_click = models.ForeignKey(WhatsAppOfferClick, null=True, blank=True, on_delete=models.SET_NULL)
	presence_confirmed_at = models.DateTimeField(null=True, blank=True)
	schedule_revision = models.PositiveIntegerField(default=0)
	completed_at = models.DateTimeField(null=True, blank=True)


class WhatsAppDraftOrder(models.Model):
	class Status(models.TextChoices):
		DRAFT = "draft", "Brouillon"
		AWAITING_CONFIRMATION = "awaiting_confirmation", "En attente de confirmation"
		CONFIRMED = "confirmed", "Confirmée"
		CANCELLED = "cancelled", "Annulée"

	business = models.ForeignKey(
		"business.BusinessProfile",
		on_delete=models.CASCADE,
		related_name="whatsapp_draft_orders",
	)
	connection = models.ForeignKey(
		BusinessWhatsAppConnection,
		on_delete=models.CASCADE,
		related_name="draft_orders",
	)
	contact = models.ForeignKey(
		BusinessWhatsAppContact,
		on_delete=models.CASCADE,
		related_name="draft_orders",
	)
	catalog_item = models.ForeignKey(
		"business.BusinessCatalogItem",
		on_delete=models.PROTECT,
		related_name="whatsapp_draft_orders",
	)
	source_click = models.ForeignKey(WhatsAppOfferClick, null=True, blank=True, on_delete=models.SET_NULL)
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=12, decimal_places=2)
	total_price = models.DecimalField(max_digits=12, decimal_places=2)
	status = models.CharField(
		max_length=32,
		choices=Status.choices,
		default=Status.DRAFT,
		db_index=True,
	)
	confirmation_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	audit = models.JSONField(default=dict, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	confirmed_at = models.DateTimeField(null=True, blank=True)
	follow_up_closed_at = models.DateTimeField(null=True, blank=True)
	fulfillment_stage = models.CharField(max_length=16, blank=True, choices=[("preparing", "En préparation"), ("shipped", "Expédiée")])
	delivery_note = models.CharField(max_length=240, blank=True)

	class Meta:
		ordering = ["-created_at", "-pk"]
		constraints = [
			models.UniqueConstraint(
				fields=["contact"],
				condition=models.Q(status="awaiting_confirmation"),
				name="wa_draft_one_pending_per_contact",
			),
		]


class WhatsAppCatalogChange(models.Model):
	business = models.ForeignKey("business.BusinessProfile", on_delete=models.CASCADE)
	item = models.ForeignKey("business.BusinessCatalogItem", null=True, blank=True, on_delete=models.SET_NULL)
	title = models.CharField(max_length=140)
	changes = models.JSONField(default=dict)
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class WhatsAppQuote(models.Model):
	class Status(models.TextChoices):
		DRAFT = "draft", "Brouillon"
		SENDING = "sending", "Envoi en cours"
		SENT = "sent", "Envoyé"
		ACCEPTED = "accepted", "Accepté"
		REVIEW = "review", "Envoi à vérifier"
		CLOSED = "closed", "Clôturé"

	contact = models.ForeignKey(BusinessWhatsAppContact, on_delete=models.CASCADE)
	reference = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
	subject = models.CharField(max_length=160)
	description = models.CharField(max_length=500, blank=True)
	amount = models.DecimalField(max_digits=12, decimal_places=2)
	currency = models.CharField(max_length=3, default="XAF")
	valid_until = models.DateField()
	status = models.CharField(max_length=10, default=Status.DRAFT, choices=Status.choices)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	@property
	def code(self):
		return self.reference.hex


class WhatsAppStockHold(models.Model):
	class Status(models.TextChoices):
		HELD = "held", "Réservé"
		CONSUMED = "consumed", "Sorti du stock"
		RELEASED = "released", "Restitué"

	draft = models.OneToOneField(WhatsAppDraftOrder, on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField()
	status = models.CharField(max_length=10, default=Status.HELD, choices=Status.choices)
	updated_at = models.DateTimeField(auto_now=True)


class WhatsAppWatch(models.Model):
	class Kind(models.TextChoices):
		WAITLIST = "waitlist", "Liste d’attente"
		PROPERTY = "property_alert", "Alerte nouveau bien"

	contact = models.ForeignKey(BusinessWhatsAppContact, on_delete=models.CASCADE)
	kind = models.CharField(max_length=16, choices=Kind.choices)
	service = models.ForeignKey("salonhub_salons.Service", null=True, blank=True, on_delete=models.CASCADE)
	listing = models.ForeignKey("immobilier_cameroun.Bien", null=True, blank=True, on_delete=models.CASCADE)
	criteria = models.JSONField(default=dict, blank=True)
	active = models.BooleanField(default=True)
	requested_at = models.DateTimeField(default=timezone.now)

	class Meta:
		constraints = [models.UniqueConstraint(fields=["contact", "kind"], name="wa_watch_contact_kind")]


class BusinessWhatsAppWorkflow(models.Model):
	class Kind(models.TextChoices):
		BOOKING = "booking", "Rappel de rendez-vous"
		PAYMENT = "payment", "Relance de paiement"
		AFTER_BOOKING = "after_booking", "Suivi après un rendez-vous"
		AFTER_ORDER = "after_order", "Suivi après une livraison"
		WAITLIST = "waitlist", "Place disponible sur liste d’attente"
		PROPERTY = "property_alert", "Nouveau bien compatible"
		SHIPPING = "shipping", "Notification d’expédition"

	business = models.ForeignKey("business.BusinessProfile", on_delete=models.CASCADE)
	kind = models.CharField(max_length=16, choices=Kind.choices)
	enabled = models.BooleanField(default=False)
	delay_hours = models.PositiveSmallIntegerField(default=24)
	template_name = models.CharField(max_length=128, blank=True)
	template_language = models.CharField(max_length=32, default="fr")
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [models.UniqueConstraint(fields=["business", "kind"], name="wa_workflow_business_kind")]


class ScheduledBusinessWhatsAppMessage(models.Model):
	class Status(models.TextChoices):
		SCHEDULED = "scheduled", "Planifié"
		SENDING = "sending", "En cours"
		SENT = "sent", "Accepté par Meta"
		FAILED = "failed", "Échec"
		CANCELLED = "cancelled", "Annulé"

	contact = models.ForeignKey(
		BusinessWhatsAppContact,
		on_delete=models.CASCADE,
		related_name="scheduled_messages",
	)
	connection = models.ForeignKey(
		BusinessWhatsAppConnection,
		on_delete=models.CASCADE,
		related_name="scheduled_messages",
	)
	template_name = models.CharField(max_length=128)
	template_language = models.CharField(max_length=32)
	body_parameters = models.JSONField(default=list, blank=True)
	scheduled_for = models.DateTimeField(db_index=True)
	status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED, db_index=True)
	wa_message_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
	delivery_status = models.CharField(max_length=24, blank=True)
	workflow = models.ForeignKey(BusinessWhatsAppWorkflow, null=True, blank=True, on_delete=models.CASCADE)
	workflow_booking = models.ForeignKey(BusinessWhatsAppBooking, null=True, blank=True, on_delete=models.SET_NULL)
	workflow_order = models.ForeignKey(WhatsAppDraftOrder, null=True, blank=True, on_delete=models.SET_NULL)
	workflow_watch = models.ForeignKey(WhatsAppWatch, null=True, blank=True, on_delete=models.SET_NULL)
	workflow_match = models.CharField(max_length=100, blank=True)
	workflow_key = models.CharField(max_length=160, unique=True, null=True, blank=True)
	workflow_revision = models.DateTimeField(null=True, blank=True)
	workflow_phone = models.CharField(max_length=64, blank=True)
	workflow_token = models.UUIDField(default=uuid.uuid4, editable=False)
	workflow_action = models.CharField(max_length=16, blank=True)
	workflow_responded_at = models.DateTimeField(null=True, blank=True)
	last_error = models.CharField(max_length=500, blank=True)
	created_by = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name="scheduled_business_whatsapp_messages",
	)
	sent_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["scheduled_for", "pk"]
		indexes = [models.Index(fields=["status", "scheduled_for"])]


class ProductWhatsAppSync(models.Model):
	boutique_product_id = models.IntegerField(db_index=True)
	waba_id = models.CharField(max_length=64, db_index=True)
	whatsapp_product_id = models.CharField(max_length=128, blank=True)
	sync_status = models.CharField(max_length=24, default="pending", db_index=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["boutique_product_id", "waba_id"],
				name="wa_commerce_product_waba_uniq",
			),
		]
		ordering = ["-last_synced_at", "-pk"]


class BusinessCatalogWhatsAppSync(models.Model):
	"""Sync state for one Business catalog item in its own connected WABA catalog."""

	class Status(models.TextChoices):
		PENDING = "pending", "En attente"
		SYNCED = "synced", "Synchronisé"
		FAILED = "failed", "Échec"
		SKIPPED = "skipped", "Ignoré"

	business_catalog_item = models.ForeignKey(
		"business.BusinessCatalogItem",
		on_delete=models.CASCADE,
		related_name="whatsapp_syncs",
	)
	connection = models.ForeignKey(
		BusinessWhatsAppConnection,
		on_delete=models.CASCADE,
		related_name="catalog_syncs",
	)
	retailer_id = models.CharField(max_length=128)
	whatsapp_product_id = models.CharField(max_length=128, blank=True)
	sync_status = models.CharField(max_length=24, choices=Status.choices, default=Status.PENDING, db_index=True)
	last_error = models.CharField(max_length=500, blank=True)
	last_synced_at = models.DateTimeField(null=True, blank=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(
				fields=["business_catalog_item", "connection"],
				name="wa_biz_item_conn_sync_uniq",
			),
		]
		ordering = ["-last_synced_at", "-pk"]
		indexes = [models.Index(fields=["connection", "sync_status"])]


class ProductView(models.Model):
	boutique_product_id = models.IntegerField(db_index=True)
	visitor_session_key = models.CharField(max_length=64, blank=True, db_index=True)
	visitor_phone = models.CharField(max_length=30, null=True, blank=True, db_index=True)
	visitor_ip = models.GenericIPAddressField(null=True, blank=True)
	viewed_at = models.DateTimeField(auto_now_add=True, db_index=True)
	converted = models.BooleanField(default=False, db_index=True)
	abandoned_sent = models.BooleanField(default=False, db_index=True)
	whatsapp_opt_in = models.BooleanField(default=False)

	class Meta:
		indexes = [models.Index(fields=["converted", "abandoned_sent", "viewed_at"]) ]
		ordering = ["-viewed_at"]


class WhatsAppProviderConfig(models.Model):
	boutique_id = models.IntegerField(db_index=True)
	waba_id = models.CharField(max_length=64)
	phone_number_id = models.CharField(max_length=64)
	catalog_id = models.CharField(max_length=64, blank=True)
	display_phone_number = models.CharField(max_length=32, blank=True)
	access_token_encrypted = models.TextField(blank=True)
	is_active = models.BooleanField(default=True, db_index=True)

	class Meta:
		constraints = [
			models.UniqueConstraint(fields=["boutique_id"], name="wa_commerce_boutique_config_uniq"),
		]
		ordering = ["boutique_id"]

	def set_access_token(self, token):
		from .security import encrypt_access_token

		self.access_token_encrypted = encrypt_access_token(token)

	def get_access_token(self):
		from .security import decrypt_access_token

		return decrypt_access_token(self.access_token_encrypted)
