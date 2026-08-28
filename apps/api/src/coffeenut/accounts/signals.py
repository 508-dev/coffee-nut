from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile, User


@receiver(post_save, sender=User)
def ensure_profile(sender: type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """Every user has a profile.

    A signal rather than manager logic, so users created by fixtures, the admin,
    or ``createsuperuser`` are covered too.
    """
    if created:
        Profile.objects.get_or_create(user=instance)
