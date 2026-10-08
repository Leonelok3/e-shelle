from django.conf import settings
from django.db import models


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
	last_error = models.CharField(max_length=500, blank=True)
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
	last_inbound_at = models.DateTimeField(null=True, blank=True, db_index=True)
	pipeline_status = models.CharField(
		max_length=16,
		choices=PipelineStatus.choices,
		default=PipelineStatus.NEW,
		db_index=True,
	)
	tags = models.JSONField(default=list, blank=True)
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
	direction = models.CharField(max_length=12, choices=Direction.choices)
	message_type = models.CharField(max_length=32, default="text")
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
