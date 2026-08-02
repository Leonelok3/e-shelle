from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import OwnerSignUpForm


class OwnerSignUpView(CreateView):
    form_class = OwnerSignUpForm
    template_name = "accounts/signup_owner.html"
    success_url = reverse_lazy("salonhub_dashboard:home")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response
