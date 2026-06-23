from django import forms
from businesses.models import Business, BusinessPhoto
from .models import AdProject


class BusinessForm(forms.ModelForm):
    class Meta:
        model = Business
        fields = ['name', 'sector', 'city', 'whatsapp', 'phone', 'promotional_offer', 'description']


class PhotoUploadForm(forms.Form):
    # We handle multiple file uploads manually in the view using request.FILES.getlist('photos')
    pass


class AdCreateForm(forms.ModelForm):
    class Meta:
        model = AdProject
        fields = ['duration_seconds']
