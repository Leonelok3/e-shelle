from django import forms
class RedeemCodeForm(forms.Form):
    code = forms.CharField(label="Code prépayé", max_length=32,
        widget=forms.TextInput(attrs={"placeholder":"ABCD-1234-XYZ","class":"form-input"}))
class FakeTopupForm(forms.Form):
    amount = forms.IntegerField(min_value=1, label="Montant (Shelles)",
        widget=forms.NumberInput(attrs={"class":"form-input"}))
    note = forms.CharField(required=False, label="Note",
        widget=forms.TextInput(attrs={"class":"form-input","placeholder":"test, cadeau…"}))
