from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(
    GOOGLE_OAUTH_CLIENT_ID="",
    GOOGLE_OAUTH_CLIENT_SECRET="",
    X_OAUTH_CLIENT_ID="",
    X_OAUTH_CLIENT_SECRET="",
)
class AuthPagesWithoutSocialTest(TestCase):
    def test_login_hides_social_buttons(self):
        response = self.client.get(reverse("users:login"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Continue with Google")
        self.assertNotContains(response, "Continue with X")

    def test_register_hides_social_buttons(self):
        response = self.client.get(reverse("users:register"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Sign up with Google")
        self.assertNotContains(response, "Sign up with X")

    def test_login_inputs_are_ltr(self):
        response = self.client.get(reverse("users:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'dir="ltr"')

    def test_register_has_no_last_name_and_ltr_non_name_inputs(self):
        response = self.client.get(reverse("users:register"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="id_last_name"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')
        self.assertContains(response, 'dir="ltr"')


@override_settings(
    GOOGLE_OAUTH_CLIENT_ID="google-client",
    GOOGLE_OAUTH_CLIENT_SECRET="google-secret",
    X_OAUTH_CLIENT_ID="x-client",
    X_OAUTH_CLIENT_SECRET="x-secret",
)
class AuthPagesWithSocialTest(TestCase):
    def test_login_shows_social_buttons(self):
        response = self.client.get(reverse("users:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/accounts/google/login/?process=login")
        self.assertContains(response, "/accounts/twitter/login/?process=login")

    def test_register_shows_social_buttons(self):
        response = self.client.get(reverse("users:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/accounts/google/login/?process=signup")
        self.assertContains(response, "/accounts/twitter/login/?process=signup")
