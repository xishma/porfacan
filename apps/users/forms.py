from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

User = get_user_model()


class TailwindAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
    )

    password = forms.CharField(
        label="رمز عبور",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"}),
    )


class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"
        self.fields["email"].widget = forms.EmailInput(attrs={"class": base_class})
        self.fields["first_name"].widget = forms.TextInput(attrs={"class": base_class})
        self.fields["last_name"].widget = forms.TextInput(attrs={"class": base_class})
        self.fields["password1"].widget.attrs["class"] = base_class
        self.fields["password2"].widget.attrs["class"] = base_class
