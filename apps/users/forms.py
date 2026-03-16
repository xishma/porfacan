from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from hcaptcha_field import hCaptchaField

User = get_user_model()


class TailwindAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(
            attrs={
                "class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2 text-left",
                "autocomplete": "email",
                "autofocus": True,
                "dir": "ltr",
            }
        ),
    )

    password = forms.CharField(
        label="رمز عبور",
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2 text-left",
                "autocomplete": "current-password",
                "dir": "ltr",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if settings.HCAPTCHA_SITEKEY:
            self.fields["hcaptcha"] = hCaptchaField(label="")


class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("email", "first_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"
        self.fields["email"].widget = forms.EmailInput(
            attrs={
                "class": f"{base_class} text-left",
                "autocomplete": "email",
                "autofocus": True,
                "dir": "ltr",
            }
        )
        self.fields["first_name"].widget = forms.TextInput(
            attrs={"class": base_class, "autocomplete": "given-name"}
        )
        self.fields["password1"].widget.attrs["class"] = base_class
        self.fields["password1"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password1"].widget.attrs["dir"] = "ltr"
        self.fields["password1"].widget.attrs["class"] = f"{base_class} text-left"
        self.fields["password2"].widget.attrs["class"] = base_class
        self.fields["password2"].widget.attrs["autocomplete"] = "new-password"
        self.fields["password2"].widget.attrs["dir"] = "ltr"
        self.fields["password2"].widget.attrs["class"] = f"{base_class} text-left"
        if settings.HCAPTCHA_SITEKEY:
            self.fields["hcaptcha"] = hCaptchaField(label="")


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "email")

    def __init__(self, *args, can_change_email: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"
        self.fields["first_name"].widget = forms.TextInput(
            attrs={"class": base_class, "autocomplete": "given-name"}
        )
        self.fields["email"].widget = forms.EmailInput(
            attrs={"class": f"{base_class} text-left", "autocomplete": "email", "dir": "ltr"}
        )
        self.can_change_email = can_change_email
        if not can_change_email:
            self.fields["email"].disabled = True
            self.fields["email"].help_text = _(
                "Email is managed by your social login provider and cannot be changed here."
            )
