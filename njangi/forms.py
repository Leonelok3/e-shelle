"""
Njangi+ — Formulaires
"""
from django import forms
from django.utils import timezone
from .models import Group, Membership, Session, Contribution, FundDeposit, Loan, LoanRepayment


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = [
            "name",
            "meeting_type",
            "frequency",
            "contribution_amount",
            "fund_loan_rate",
            "fund_deposit_rate",
            "base_fund_required",
            "penalty_per_day",
            "description",
            "logo",
        ]
        labels = {
            "name": "Nom de la réunion",
            "frequency": "Fréquence des séances",
            "contribution_amount": "Cotisation par membre (FCFA)",
            "fund_loan_rate": "Taux d'intérêt sur les prêts (%)",
            "fund_deposit_rate": "Bénéfice versé aux épargnants (%)",
            "base_fund_required": "Fond de caisse / Secours par membre (FCFA)",
            "penalty_per_day": "Pénalité en cas d'absence (FCFA)",
            "description": "Description ou devise de la réunion (facultatif)",
            "logo": "Photo ou logo du groupe (facultatif)",
        }
        help_texts = {
            "name": "Ex: Réunion Familiale, Amicale des Commerçants, Anciens Étudiants...",
            "meeting_type": "Choisissez le type qui correspond à votre groupe.",
            "frequency": "À quel rythme les membres se réunissent pour cotiser.",
            "contribution_amount": "Somme versée par chaque membre à chaque séance.",
            "fund_loan_rate": "Pourcentage d'intérêt par mois. Ex: 10% (sur 50 000 FCFA prêtés, le membre rembourse 55 000 FCFA).",
            "fund_deposit_rate": "Gain mensuel pour le membre qui dépose de l'argent dans la caisse de prêt (ex: 5%).",
            "base_fund_required": "Caisse de réserve ou de secours (facultatif). Laissez 0 si vous n'en avez pas.",
            "penalty_per_day": "Montant prélevé si un membre est absent sans motif valable.",
            "description": "Présentez brièvement le but ou la devise de votre groupe.",
        }
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Ex : Réunion Familiale Étoile"}),
            "contribution_amount": forms.NumberInput(attrs={"placeholder": "Ex : 10000", "min": "100"}),
            "fund_loan_rate": forms.NumberInput(attrs={"placeholder": "10", "min": "0", "step": "0.5"}),
            "fund_deposit_rate": forms.NumberInput(attrs={"placeholder": "5", "min": "0", "step": "0.5"}),
            "base_fund_required": forms.NumberInput(attrs={"placeholder": "0", "min": "0"}),
            "penalty_per_day": forms.NumberInput(attrs={"placeholder": "1000", "min": "0"}),
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "Ex : Fraternité, entraide et développement mutuel..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            if not self.initial.get("fund_loan_rate"):
                self.initial["fund_loan_rate"] = 10
            if not self.initial.get("fund_deposit_rate"):
                self.initial["fund_deposit_rate"] = 5
            if not self.initial.get("base_fund_required"):
                self.initial["base_fund_required"] = 0
            if not self.initial.get("penalty_per_day"):
                self.initial["penalty_per_day"] = 1000

    def save(self, commit=True):
        if not self.instance.pk and not self.instance.start_date:
            self.instance.start_date = timezone.localdate()
        return super().save(commit=commit)


class JoinGroupForm(forms.Form):
    invite_code = forms.CharField(
        max_length=8,
        label="Code d'invitation",
        widget=forms.TextInput(attrs={"placeholder": "Ex : NJANG123", "class": "uppercase"}),
    )

    def clean_invite_code(self):
        return self.cleaned_data["invite_code"].upper()


class SessionCreateForm(forms.ModelForm):
    class Meta:
        model = Session
        fields = [
            "session_number", "date",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group:
            # Pré-remplir le numéro de séance
            last = group.sessions.order_by("-session_number").first()
            self.fields["session_number"].initial = (last.session_number + 1) if last else 1


class ContributionPayForm(forms.Form):
    PAYMENT_METHOD_CHOICES = [
        ("mtn_momo",    "MTN Mobile Money"),
        ("orange_money","Orange Money"),
        ("cash",        "Espèces"),
        ("transfer",    "Virement"),
    ]
    amount         = forms.DecimalField(max_digits=12, decimal_places=0, min_value=1)
    payment_method = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    transaction_ref = forms.CharField(max_length=100, required=False, label="Référence (optionnel)")


class LoanRequestForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ["membership", "amount_requested", "duration_months", "guarantor", "purpose"]
        widgets = {
            "purpose": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            memberships = Membership.objects.filter(user=user, is_active=True).select_related("group")
            self.fields["membership"].queryset = memberships
            # Garantisseurs = autres membres actifs des mêmes groupes
            groups = memberships.values_list("group", flat=True)
            self.fields["guarantor"].queryset = Membership.objects.filter(
                group__in=groups, is_active=True
            ).exclude(user=user).select_related("user", "group")
            self.fields["guarantor"].required = False


class DepositCreateForm(forms.ModelForm):
    class Meta:
        model = FundDeposit
        fields = ["membership", "amount", "payment_method", "transaction_ref"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user:
            self.fields["membership"].queryset = Membership.objects.filter(
                user=user, is_active=True
            ).select_related("group")
        self.fields["payment_method"].widget = forms.Select(choices=[
            ("mtn_momo",    "MTN Mobile Money"),
            ("orange_money","Orange Money"),
            ("cash",        "Espèces"),
            ("transfer",    "Virement"),
        ])
        self.fields["transaction_ref"].required = False


class RepaymentForm(forms.Form):
    PAYMENT_METHOD_CHOICES = [
        ("mtn_momo",    "MTN Mobile Money"),
        ("orange_money","Orange Money"),
        ("cash",        "Espèces"),
        ("transfer",    "Virement"),
    ]
    amount          = forms.DecimalField(max_digits=14, decimal_places=0, min_value=1)
    payment_method  = forms.ChoiceField(choices=PAYMENT_METHOD_CHOICES)
    transaction_ref = forms.CharField(max_length=100, required=False, label="Référence (optionnel)")


class SessionFinancialForm(forms.ModelForm):

    class Meta:
        model = Session
        fields = [
            "proposals",
            "notes",
            "loan_fund_available",
            "cash_returned_manual",
        ]
        widgets = {
            "proposals": forms.Textarea(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "rows": 4,
                "placeholder": "Propositions, décisions et sujets à suivre...",
            }),
            "notes": forms.Textarea(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "rows": 3,
                "placeholder": "Résumez le déroulement de la séance et les décisions prises...",
            }),
            "loan_fund_available": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "min": "0",
            }),
            "cash_returned_manual": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "min": "0",
            }),
        }

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.status in ("completed", "cancelled"):
            self.fields["loan_fund_available"].disabled = True
            self.fields["cash_returned_manual"].disabled = True
