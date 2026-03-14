from django.contrib.auth import get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import TailwindAuthenticationForm, UserRegistrationForm

User = get_user_model()


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = TailwindAuthenticationForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("lexicon:entry-list")


class UserRegisterView(CreateView):
    model = User
    form_class = UserRegistrationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("users:login")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.role = User.Roles.CONTRIBUTOR
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())
