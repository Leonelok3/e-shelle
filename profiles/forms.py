from django import forms
from .models import Profile, PortfolioItem
from .models import Profile



class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "category",
            "headline",
            "location",
            "bio",
            "linkedin_url",
            "avatar",
        ]
        widgets = {
            "category": forms.Select(attrs={"class": "profile-input"}),
            "headline": forms.TextInput(attrs={"class": "profile-input"}),
            "location": forms.TextInput(attrs={"class": "profile-input"}),
            "bio": forms.Textarea(attrs={"class": "profile-input"}),
            "linkedin_url": forms.URLInput(attrs={"class": "profile-input"}),
        }


class PortfolioItemForm(forms.ModelForm):
    class Meta:
        model = PortfolioItem
        fields = ['title', 'item_type', 'file', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'item_type': forms.Select(attrs={'class': 'form-select'}),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
        }

class ContactCandidateForm(forms.Form):
    recruiter_name = forms.CharField(label="Votre nom", widget=forms.TextInput(attrs={'class': 'form-control'}))
    recruiter_email = forms.EmailField(label="Votre email", widget=forms.EmailInput(attrs={'class': 'form-control'}))
    message = forms.CharField(widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}), label="Message")




class AvatarUploadForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ["avatar"]

    def clean_avatar(self):
        avatar = self.cleaned_data.get("avatar")

        if avatar:
            # Taille max : 2 Mo
            if avatar.size > 2 * 1024 * 1024:
                raise forms.ValidationError("Image trop lourde (max 2 Mo).")

            # Types autorisés
            if not avatar.content_type in ["image/jpeg", "image/png"]:
                raise forms.ValidationError("Format non supporté (JPG / PNG uniquement).")

        return avatar
