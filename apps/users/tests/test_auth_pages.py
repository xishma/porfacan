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
        self.assertContains(response, "Continue with Google")
        self.assertContains(response, "Continue with X")

    def test_register_shows_social_buttons(self):
        response = self.client.get(reverse("users:register"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign up with Google")
        self.assertContains(response, "Sign up with X")
