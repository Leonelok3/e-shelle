from django import forms
from .models import Profile, PortfolioItem

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['category', 'headline', 'location', 'bio', 'linkedin_url', 'avatar']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'headline': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
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