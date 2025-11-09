from django import forms
from .models import Photo

from django import forms

PHOTO_TYPE_CHOICES = [
    ("dv_lottery", "DV Lottery (600×600)"),
    ("passport", "Passeport"),
    ("visa_generic", "Visa (générique)"),
]

class UploadPhotoForm(forms.Form):
    photo_type = forms.ChoiceField(choices=PHOTO_TYPE_CHOICES, label="Type de photo")
    image = forms.ImageField(label="Image (JPEG/PNG)")
    
class PhotoForm(forms.ModelForm):
    class Meta:
        model = Photo
        fields = ["photo_type", "image"]
        widgets = {
            "photo_type": forms.Select(attrs={"class": "form-select"}),
            "image": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
        labels = {
            "photo_type": "Choisir le type de photo",
            "image": "Téléverser une photo (JPEG/PNG)",
        }
