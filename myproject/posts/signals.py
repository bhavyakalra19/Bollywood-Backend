import logging
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import UserFCMToken
from accounts.services import sync_user_fcm_token_flag_by_id
from .models import Post

logger = logging.getLogger(__name__)


def _get_firebase_app():
    try:
        import firebase_admin
        from firebase_admin import credentials
    except Exception:
        logger.exception("firebase_admin import failed. Skipping notifications.")
        return None

    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    creds_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
    if not creds_path:
        logger.warning("FIREBASE_CREDENTIALS_PATH is not configured. Skipping notifications.")
        return None

    cred_file = Path(creds_path)
    if not cred_file.exists():
        logger.warning("Firebase credentials file not found at %s. Skipping notifications.", creds_path)
        return None

    try:
        cred = credentials.Certificate(str(cred_file))
        return firebase_admin.initialize_app(cred)
    except Exception:
        logger.exception("Failed to initialize Firebase app.")
        return None


def _deactivate_invalid_tokens(invalid_token_records):
    if not invalid_token_records:
        return

    user_ids = {record.user_id for record in invalid_token_records}
    UserFCMToken.objects.filter(id__in=[record.id for record in invalid_token_records]).update(is_active=False)
    for user_id in user_ids:
        sync_user_fcm_token_flag_by_id(user_id)


def send_post_created_notifications(post):
    app = _get_firebase_app()
    if app is None:
        return

    try:
        from firebase_admin import messaging
    except Exception:
        logger.exception("firebase_admin.messaging import failed. Skipping notifications.")
        return

    active_tokens = list(
        UserFCMToken.objects.select_related("user")
        .filter(is_active=True)
        .exclude(token="")
    )
    if not active_tokens:
        return

    token_values = [row.token for row in active_tokens]
    multicast = messaging.MulticastMessage(
        tokens=token_values,
        notification=messaging.Notification(
            title="New Post Available",
            body=post.title,
        ),
        data={
            "post_id": str(post.id),
            "type": "new_post",
        },
    )

    invalid_records = []
    try:
        # Per-token result API in firebase-admin Python
        batch_response = messaging.send_each_for_multicast(multicast, app=app)
        for idx, response in enumerate(batch_response.responses):
            if response.success:
                continue
            error_code = getattr(response.exception, "code", "") or ""
            if error_code in {"registration-token-not-registered", "invalid-argument", "unregistered"}:
                invalid_records.append(active_tokens[idx])
            else:
                logger.warning("FCM send failed for token id=%s: %s", active_tokens[idx].id, response.exception)
    except Exception:
        logger.exception("Error while sending FCM notifications.")
        return

    _deactivate_invalid_tokens(invalid_records)


@receiver(post_save, sender=Post)
def post_created_notify_users(sender, instance, created, **kwargs):
    if not created or not instance.is_active:
        return

    transaction.on_commit(lambda: send_post_created_notifications(instance))
