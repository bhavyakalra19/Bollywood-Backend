from datetime import timedelta
from secrets import choice
from string import digits

import requests
from django.conf import settings
from django.utils import timezone

from .models import RegistrationOTP, User


class OTPDeliveryError(Exception):
    pass


def _send_registration_otp_email(recipient_email, otp_code):
    resend_api_key = getattr(settings, "RESEND_API_KEY", "")
    resend_api_url = getattr(settings, "RESEND_API_URL", "https://api.resend.com/emails")

    if not resend_api_key:
        raise OTPDeliveryError("RESEND_API_KEY is not configured.")

    payload = {
        "from": "noreply@auditionbollywood.blog",
        "to": [recipient_email],
        "subject": "Your registration OTP",
        "text": f"Your OTP is {otp_code}. It expires in {getattr(settings, 'OTP_EXPIRY_SECONDS', 300)} seconds.",
    }

    response = requests.post(
        resend_api_url,
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=getattr(settings, "RESEND_TIMEOUT", getattr(settings, "EMAIL_TIMEOUT", 10)),
    )

    if response.status_code < 200 or response.status_code >= 300:
        raise OTPDeliveryError(
            f"Resend API error: {response.status_code} {response.text[:200]}"
        )


def _generate_otp(length=6):
    return "".join(choice(digits) for _ in range(length))


def _otp_expiry_time():
    ttl_seconds = getattr(settings, "OTP_EXPIRY_SECONDS", 300)
    return timezone.now() + timedelta(seconds=ttl_seconds)


def request_registration_otp(channel, target_value):
    now = timezone.now()
    RegistrationOTP.objects.filter(
        otp_type=channel,
        target_value=target_value,
        is_consumed=False,
        expires_at__gt=now,
    ).update(is_consumed=True, consumed_at=now)

    otp_code = _generate_otp()
    otp = RegistrationOTP.objects.create(
        otp_type=channel,
        target_value=target_value,
        code=otp_code,
        expires_at=_otp_expiry_time(),
    )

    if channel == RegistrationOTP.OTPType.EMAIL:
        try:
            _send_registration_otp_email(target_value, otp_code)
        except Exception as exc:
            # Mark the OTP unusable if delivery fails to avoid dangling valid codes.
            otp.is_consumed = True
            otp.consumed_at = timezone.now()
            otp.save(update_fields=["is_consumed", "consumed_at", "updated_at"])
            raise OTPDeliveryError(f"Unable to send OTP email right now. {exc}") from exc

    return otp


def verify_registration_otp(channel, target_value, otp_code):
    now = timezone.now()
    otp = (
        RegistrationOTP.objects.filter(
            otp_type=channel,
            target_value=target_value,
            code=otp_code,
            is_consumed=False,
            expires_at__gt=now,
        )
        .order_by("-created_at")
        .first()
    )

    if not otp:
        return False

    otp.is_verified = True
    otp.verified_at = now
    otp.save(update_fields=["is_verified", "verified_at", "updated_at"])
    return True


def consume_verified_registration_otp(channel, target_value, otp_code):
    now = timezone.now()
    otp = (
        RegistrationOTP.objects.filter(
            otp_type=channel,
            target_value=target_value,
            code=otp_code,
            is_verified=True,
            is_consumed=False,
            expires_at__gt=now,
        )
        .order_by("-verified_at", "-created_at")
        .first()
    )

    if not otp:
        return False

    otp.is_consumed = True
    otp.consumed_at = now
    otp.save(update_fields=["is_consumed", "consumed_at", "updated_at"])
    return True


def sync_user_fcm_token_flag(user):
    has_active_tokens = user.fcm_tokens.filter(is_active=True).exists()
    if user.fcm_token != has_active_tokens:
        user.fcm_token = has_active_tokens
        user.save(update_fields=["fcm_token", "updated_at"])
    return has_active_tokens


def sync_user_fcm_token_flag_by_id(user_id):
    user = User.objects.filter(id=user_id).first()
    if not user:
        return False
    return sync_user_fcm_token_flag(user)
