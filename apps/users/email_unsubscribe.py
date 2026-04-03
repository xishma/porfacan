"""Signed tokens for one-click email preference links (no login)."""

from django.core.signing import BadSignature, Signer

_EMAIL_NOTIFICATIONS_SALT = "porfacan.email-notifications-unsub"


def sign_email_notifications_unsubscribe(user_id: int) -> str:
    signer = Signer(salt=_EMAIL_NOTIFICATIONS_SALT)
    return signer.sign(str(int(user_id)))


def unsign_email_notifications_unsubscribe(signed: str) -> int | None:
    signer = Signer(salt=_EMAIL_NOTIFICATIONS_SALT)
    try:
        return int(signer.unsign(signed))
    except (BadSignature, ValueError):
        return None
