"""
Formulaires de gestion du contenu (admin custom).
"""
from django import forms
from edu_platform.models import Subject, ExamDocument, VideoLesson


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = [
            'title', 'subject_type', 'level', 'year',
            'description', 'thumbnail', 'is_premium',
            'is_published', 'order', 'allowed_plans'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'subject_type': forms.Select(attrs={'class': 'form-select'}),
            'level': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'ex: 2024'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'allowed_plans': forms.CheckboxSelectMultiple(),
        }


class ExamDocumentForm(forms.ModelForm):
    class Meta:
        model = ExamDocument
        fields = ['subject', 'doc_type', 'title', 'file', 'preview_pages', 'is_downloadable']
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'doc_type': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'preview_pages': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class VideoLessonForm(forms.ModelForm):
    class Meta:
        model = VideoLesson
        fields = [
            'subject', 'title', 'description', 'video_url',
            'video_file', 'duration_minutes', 'thumbnail', 'is_preview', 'order'
        ]
        widgets = {
            'subject': forms.Select(attrs={'class': 'form-select'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'video_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://youtube.com/...'}),
            'duration_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
