from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q

from .models import Profile, Category, PortfolioItem
from .forms import ProfileForm, PortfolioItemForm, ContactCandidateForm

# Page d'accueil de l'application (Liste des profils)
class ProfileListView(ListView):
    model = Profile
    template_name = 'profiles/profile_list.html'
    context_object_name = 'profiles'
    paginate_by = 12

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.GET.get('category')
        query = self.request.GET.get('q')

        if category:
            queryset = queryset.filter(category__slug=category)
        if query:
            queryset = queryset.filter(
                Q(headline__icontains=query) | 
                Q(bio__icontains=query) |
                Q(location__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        return context

# Détail d'un profil
class ProfileDetailView(DetailView):
    model = Profile
    template_name = 'profiles/profile_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['contact_form'] = ContactCandidateForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ContactCandidateForm(request.POST)
        if form.is_valid():
            # Simulation envoi email (s'affiche dans la console)
            print(f"EMAIL ENVOYÉ À {self.object.user.email} : {form.cleaned_data['message']}")
            messages.success(request, "Votre message a été envoyé !")
            return redirect('profiles:detail', pk=self.object.pk)
        
        context = self.get_context_data()
        context['contact_form'] = form
        return render(request, self.template_name, context)

# Création de profil
class ProfileCreateView(LoginRequiredMixin, CreateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'profiles/profile_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, "Profil créé avec succès !")
        return super().form_valid(form)

# Édition de profil
class ProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = 'profiles/profile_form.html'

    def test_func(self):
        return self.request.user == self.get_object().user

# Ajouter un fichier au portfolio
def add_portfolio_item(request, pk):
    profile = get_object_or_404(Profile, pk=pk)
    if request.user != profile.user:
        return redirect('profiles:list')
    
    if request.method == 'POST':
        form = PortfolioItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.profile = profile
            item.save()
            messages.success(request, "Fichier ajouté !")
            return redirect('profiles:detail', pk=pk)
    else:
        form = PortfolioItemForm()
    
    return render(request, 'profiles/portfolio_form.html', {'form': form, 'profile': profile})