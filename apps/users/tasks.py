import logging

from celery import shared_task
from allauth.account.models import EmailAddress
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=5, default_retry_delay=2)
def send_verification_email_task(self, email_address_id: int, signup: bool = False) -> None:
    try:
        email_address = EmailAddress.objects.select_related("user").get(pk=email_address_id)
    except EmailAddress.DoesNotExist:
        logger.warning(
            "Verification email skipped: EmailAddress %s does not exist yet. Retrying.",
            email_address_id,
        )
        raise self.retry()

    if email_address.verified:
        logger.info(
            "Verification email skipped: EmailAddress %s is already verified.",
            email_address_id,
        )
        return

    cooldown_seconds = max(int(getattr(settings, "VERIFICATION_EMAIL_COOLDOWN_SECONDS", 300)), 0)
    cooldown_key = f"users:verification-email:{email_address.email.lower()}"
    if cooldown_seconds > 0 and not cache.add(cooldown_key, "1", timeout=cooldown_seconds):
        logger.info(
            "Verification email skipped: cooldown active for %s.",
            email_address.email,
        )
        return

    try:
        email_address.send_confirmation(request=None, signup=signup)
    except Exception:
        # Allow immediate retry if sending fails after we consumed cooldown.
        if cooldown_seconds > 0:
            cache.delete(cooldown_key)
        raise
