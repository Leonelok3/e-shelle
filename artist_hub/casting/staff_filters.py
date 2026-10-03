from django import forms
from django.db.models import Q
from .models import Candidate, CastingSession, CandidateStatus, CandidateGender

class StaffFilterForm(forms.Form):
    session = forms.ModelChoiceField(queryset=CastingSession.objects.none(), required=False, label="Session")
    status = forms.ChoiceField(choices=[("", "Tous les statuts")] + list(CandidateStatus.choices), required=False, label="Statut")
    gender = forms.ChoiceField(choices=[("", "Tous")] + list(CandidateGender.choices), required=False, label="Sexe")
    city = forms.CharField(required=False, max_length=150, label="Ville")
    paid = forms.ChoiceField(choices=[("", "Tous"), ("yes", "Payés"), ("no", "Non payés")], required=False, label="Paiement")
    minor = forms.ChoiceField(choices=[("", "Tous"), ("yes", "Mineurs"), ("no", "Majeurs")], required=False, label="Âge")
    q = forms.CharField(required=False, max_length=150, label="Recherche")
    start = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Depuis")
    end = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label="Jusqu’au")
    order = forms.ChoiceField(choices=[("", "Plus récents"), ("height_desc", "Taille décroissante"),
        ("height_asc", "Taille croissante"), ("name", "Nom"), ("oldest", "Plus anciens")], required=False, label="Tri")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["session"].queryset = CastingSession.objects.order_by("-created_at")
        for field in self.fields.values():
            field.widget.attrs["class"] = "hub-select" if isinstance(field.widget, forms.Select) else "hub-input"
    def clean(self):
        values = super().clean()
        if values.get("start") and values.get("end") and values["start"] > values["end"]:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")
        return values

def filtered_candidates(params):
    form = StaffFilterForm(params)
    qs = Candidate.objects.select_related("session", "payment").prefetch_related("photos")
    if not form.is_valid():
        return qs.none(), form
    data = form.cleaned_data
    for key in ("session", "status", "gender"):
        if data.get(key): qs = qs.filter(**{key: data[key]})
    if data.get("city"): qs = qs.filter(city__icontains=data["city"])
    if data.get("paid") == "yes": qs = qs.filter(payment__status="SUCCESS")
    if data.get("paid") == "no": qs = qs.exclude(payment__status="SUCCESS")
    if data.get("minor"): qs = qs.filter(is_minor=data["minor"] == "yes")
    if data.get("start"): qs = qs.filter(created_at__date__gte=data["start"])
    if data.get("end"): qs = qs.filter(created_at__date__lte=data["end"])
    if data.get("q"):
        search = Q()
        for key in ("candidate_number", "access_code", "first_name", "last_name", "phone", "email", "city"):
            search |= Q(**{key + "__icontains": data["q"]})
        qs = qs.filter(search)
    order = {"height_desc": ("-height_cm", "-pk"), "height_asc": ("height_cm", "pk"),
             "name": ("last_name", "first_name", "pk"), "oldest": ("created_at", "pk")}
    return qs.order_by(*order.get(data.get("order"), ("-created_at", "-pk"))), form
