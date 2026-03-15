from celery import shared_task
from allauth.account.models import EmailAddress


@shared_task
def send_verification_email_task(email_address_id: int, signup: bool = False) -> None:
    try:
        email_address = EmailAddress.objects.select_related("user").get(pk=email_address_id)
    except EmailAddress.DoesNotExist:
        return

    if email_address.verified:
        return

    email_address.send_confirmation(request=None, signup=signup)
