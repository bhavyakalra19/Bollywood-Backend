from django.db.models.signals import post_delete, post_save
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone

from .models import Purchase


def _sync_user_premium(user):
    now = timezone.now()
    has_active_purchase = Purchase.objects.filter(
        user=user,
        is_active=True,
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).exists()

    if user.is_premium != has_active_purchase:
        user.is_premium = has_active_purchase
        user.save(update_fields=["is_premium", "updated_at"])


@receiver(post_save, sender=Purchase)
def update_user_premium_on_purchase_save(sender, instance, **kwargs):
    _sync_user_premium(instance.user)


@receiver(post_delete, sender=Purchase)
def update_user_premium_on_purchase_delete(sender, instance, **kwargs):
    _sync_user_premium(instance.user)
