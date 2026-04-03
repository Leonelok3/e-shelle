"""
Modèle Device Binding : enregistrement et vérification d'appareil.
"""
from django.db import models
from django.conf import settings


class DeviceBinding(models.Model):
    """
    Lie un code d'accès à un seul appareil via fingerprint composite (SHA256).
    Empêche le partage de compte entre plusieurs appareils.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='edu_devices'
    )
    access_code = models.ForeignKey(
        'edu_platform.AccessCode',
        on_delete=models.CASCADE,
        related_name='device_bindings'
    )
    # Fingerprint composite : User-Agent + Screen + Timezone + Hardware
    device_fingerprint = models.CharField(max_length=128, verbose_name='Empreinte appareil (SHA256)')
    device_label = models.CharField(max_length=100, blank=True, verbose_name='Libellé appareil')
    first_seen = models.DateTimeField(auto_now_add=True, verbose_name='Première connexion')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='Dernière connexion')
    is_primary = models.BooleanField(default=True, verbose_name='Appareil principal')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='Adresse IP')
    connection_count = models.IntegerField(default=1, verbose_name='Nombre de connexions')

    class Meta:
        verbose_name = 'Appareil enregistré'
        verbose_name_plural = 'Appareils enregistrés'
        unique_together = [('access_code', 'device_fingerprint')]
        ordering = ['-last_seen']

    def __str__(self):
        label = self.device_label or 'Appareil inconnu'
        return f"{self.user.username} — {label} [{self.device_fingerprint[:12]}...]"

    def increment_connection(self):
        """Incrémente le compteur de connexions et met à jour last_seen."""
        self.connection_count += 1
        self.save(update_fields=['connection_count', 'last_seen'])
