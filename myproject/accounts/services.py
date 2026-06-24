from datetime import timedelta
from html import escape
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

    otp_expiry_minutes = getattr(settings, "OTP_EXPIRY_SECONDS", 300) // 60
    escaped_otp = escape(str(otp_code))

    text_body = f"""Hi,

Your Audition Bollywood verification code is:

{otp_code}

This code will expire in {otp_expiry_minutes} minutes.

If you did not request this code, you can safely ignore this email.

Thanks,
Audition Bollywood Team

Audition Bollywood
https://auditionbollywood.blog/"""

    html_body = f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Your Audition Bollywood Verification Code</title>
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f9fafb; color: #1f2937;">
  <table border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f9fafb; padding: 20px 0;">
    <tr>
      <td align="center">
        <table border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
          <!-- Header -->
          <tr>
            <td style="padding: 24px; text-align: center; background-color: #ffffff; border-bottom: 1px solid #f3f4f6;">
              <span style="font-size: 20px; font-weight: bold; color: #111827; letter-spacing: 0.5px;">Audition Bollywood</span>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding: 32px 24px;">
              <p style="margin: 0 0 16px 0; font-size: 16px; line-height: 1.5; color: #374151;">Hi,</p>
              <p style="margin: 0 0 24px 0; font-size: 16px; line-height: 1.5; color: #374151;">Your Audition Bollywood verification code is:</p>
              
              <!-- OTP Box -->
              <table border="0" cellpadding="0" cellspacing="0" width="100%" style="margin-bottom: 24px;">
                <tr>
                  <td align="center">
                    <div style="background-color: #f3f4f6; border-radius: 6px; padding: 16px 24px; font-size: 32px; font-weight: bold; color: #111827; letter-spacing: 4px; display: inline-block;">
                      {escaped_otp}
                    </div>
                  </td>
                </tr>
              </table>

              <p style="margin: 0 0 16px 0; font-size: 15px; line-height: 1.5; color: #4b5563;">This code will expire in <strong>{otp_expiry_minutes} minutes</strong>.</p>
              <p style="margin: 0 0 24px 0; font-size: 14px; line-height: 1.5; color: #6b7280;">If you did not request this code, you can safely ignore this email.</p>
              
              <p style="margin: 0; font-size: 15px; line-height: 1.5; color: #374151;">Thanks,<br /><strong>Audition Bollywood Team</strong></p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding: 24px; background-color: #f9fafb; text-align: center; border-top: 1px solid #f3f4f6;">
              <p style="margin: 0 0 8px 0; font-size: 12px; color: #9ca3af;">This is an automated security notification. Please do not reply directly to this email.</p>
              <p style="margin: 0; font-size: 12px; color: #9ca3af;">&copy; 2026 Audition Bollywood. All rights reserved.</p>
              <p style="margin: 8px 0 0 0; font-size: 12px; color: #9ca3af;">
                Audition Bollywood ·
                <a href="https://auditionbollywood.blog/" style="color: #6b7280;">auditionbollywood.blog</a>
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

    payload = {
        "from": "Audition Bollywood <noreply@auditionbollywood.blog>",
        "to": [recipient_email],
        "subject": "Your Audition Bollywood verification code",
        "text": text_body,
        "html": html_body,
        "tags": [
            {
                "name": "email_type",
                "value": "registration_otp"
            }
        ]
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


def _check_otp_rate_limit(channel, target_value):
    now = timezone.now()

    # 3 per 10 minutes
    ten_mins_ago = now - timedelta(minutes=10)
    count_10m = RegistrationOTP.objects.filter(
        otp_type=channel,
        target_value=target_value,
        created_at__gte=ten_mins_ago
    ).count()
    if count_10m >= 3:
        raise OTPDeliveryError("Too many OTP requests. Please try again after 10 minutes.")

    # 8 per 1 hour
    one_hour_ago = now - timedelta(hours=1)
    count_1h = RegistrationOTP.objects.filter(
        otp_type=channel,
        target_value=target_value,
        created_at__gte=one_hour_ago
    ).count()
    if count_1h >= 8:
        raise OTPDeliveryError("Too many OTP requests. Please try again later.")


def request_registration_otp(channel, target_value):
    _check_otp_rate_limit(channel, target_value)

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
