from django.contrib import admin
from .models import VisaTourismRequest, VisaCreditWallet


@admin.register(VisaTourismRequest)
class VisaTourismRequestAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'destination',
        'nationalite',
        'pays_residence',
        'score_chances',
        'niveau_risque',
        'created_at',
    )
    list_filter = ('destination', 'pays_residence', 'niveau_risque', 'created_at')
    search_fields = ('full_name', 'email', 'nationalite', 'pays_residence')
    readonly_fields = (
        'score_chances',
        'niveau_risque',
        'points_forts',
        'points_faibles',
        'documents',
        'etapes',
        'remarques_destination',
        'conseils',
        'created_at',
    )


@admin.register(VisaCreditWallet)
class VisaCreditWalletAdmin(admin.ModelAdmin):
    list_display = ('email', 'solde', 'updated_at')
    search_fields = ('email',)
