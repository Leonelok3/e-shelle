"""
Njangi+ — Formulaires
"""
from django import forms
from .models import Group, Membership, Session, Contribution, FundDeposit, Loan, LoanRepayment


class GroupCreateForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = [
            "name", "description", "logo", "frequency",
            "contribution_amount", "max_members",
            "fund_loan_rate", "fund_deposit_rate", "penalty_per_day",
            "max_loan_multiplier", "fund_reserve_pct", "require_guarantor",
            "start_date",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }


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
            "session_number", "date", "beneficiary", "notes",
            "main_raised_amount", "loan_fund_available", "loan_interest_rate", "loan_due_date", "cash_returned_manual",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "loan_due_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, group=None, **kwargs):
        super().__init__(*args, **kwargs)
        if group:
            self.fields["beneficiary"].queryset = Membership.objects.filter(
                group=group, is_active=True
            ).select_related("user")
            self.fields["beneficiary"].required = False
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
            "main_raised_amount",
            "loan_fund_available",
            "loan_interest_rate",
            "loan_due_date",
            "cash_returned_manual",
        ]
        widgets = {
            "main_raised_amount": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "min": "0",
            }),
            "loan_fund_available": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "min": "0",
            }),
            "loan_interest_rate": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "step": "0.01",
                "min": "0",
            }),
            "loan_due_date": forms.DateInput(attrs={
                "type": "date",
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
            }),
            "cash_returned_manual": forms.NumberInput(attrs={
                "class": "w-full rounded-xl border border-gray-200 px-3 py-2",
                "min": "0",
            }),
        }
