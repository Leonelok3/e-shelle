from django.db import models


class Business(models.Model):
    name = models.CharField(max_length=220)
    sector = models.CharField(max_length=140, blank=True)
    city = models.CharField(max_length=140, blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    promotional_offer = models.CharField(max_length=220, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class BusinessPhoto(models.Model):
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='businesses/photos/')
    order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self) -> str:
        return f'{self.business_id} - photo {self.order}'
