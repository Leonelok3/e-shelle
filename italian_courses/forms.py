from django import forms
from .models import Lesson
from .sanitizer import sanitize_html

def _rich_widget():
    # Optional rich editor support:
    # - django-ckeditor: pip install django-ckeditor
    # - django-tinymce: pip install django-tinymce
    try:
        from ckeditor.widgets import CKEditorWidget  # type: ignore
        return CKEditorWidget()
    except Exception:
        pass

    try:
        from tinymce.widgets import TinyMCE  # type: ignore
        return TinyMCE(attrs={"cols": 80, "rows": 25})
    except Exception:
        pass

    return forms.Textarea(attrs={"cols": 80, "rows": 25})

class LessonAdminForm(forms.ModelForm):
    class Meta:
        model = Lesson
        fields = "__all__"
        widgets = {
            "content_html": _rich_widget(),
        }

    def clean_content_html(self):
        html = self.cleaned_data.get("content_html", "")
        return sanitize_html(html)
