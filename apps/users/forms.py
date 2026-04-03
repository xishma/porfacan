from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from hcaptcha_field import hCaptchaField

User = get_user_model()


class _PostedBooleanCheckbox(forms.CheckboxInput):
    """Checkbox + hidden 0 so unchecked state is still posted (avoids silent opt-out)."""

    def render(self, name, value, attrs=None, renderer=None):
        hidden = format_html('<input type="hidden" name="{}" value="0">', name)
        cb = super().render(name, value, attrs, renderer)
        return mark_safe(hidden + cb)

    def value_from_datadict(self, data, files, name):
        return data.get(name) == "1"


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
        fields = ("first_name", "email", "receive_email_notifications")

    def __init__(self, *args, can_change_email: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        base_class = "w-full rounded-lg border border-slate-300 ps-3 pe-3 py-2"
        self.fields["first_name"].widget = forms.TextInput(
            attrs={"class": base_class, "autocomplete": "given-name"}
        )
        self.fields["email"].widget = forms.EmailInput(
            attrs={"class": f"{base_class} text-left", "autocomplete": "email", "dir": "ltr"}
        )
        self.fields["receive_email_notifications"].required = False
        self.fields["receive_email_notifications"].widget = _PostedBooleanCheckbox(
            attrs={"class": "h-4 w-4 rounded border-slate-300 text-slate-900"}
        )
        self.can_change_email = can_change_email
        if not can_change_email:
            self.fields["email"].disabled = True
            self.fields["email"].help_text = _(
                "Email is managed by your social login provider and cannot be changed here."
            )
