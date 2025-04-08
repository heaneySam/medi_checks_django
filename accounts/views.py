from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from django.contrib.auth.views import LoginView
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .models import User

# Create your views here.

class SignUpView(CreateView):
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    template_name = 'registration/signup.html'

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response

class CustomLoginView(LoginView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, 'You are already logged in.')
            return redirect('/')
        return super().get(request, *args, **kwargs)

@login_required
def profile(request):
    if request.method == 'POST':
        form = CustomUserChangeForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')
    else:
        form = CustomUserChangeForm(instance=request.user)
    
    return render(request, 'registration/profile.html', {
        'form': form
    })

@login_required
def logout_view(request):
    logout(request)
    return redirect('accounts:login')
