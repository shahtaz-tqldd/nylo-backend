from django.db.models.signals import post_migrate
from django.dispatch import receiver

from shop.services import ensure_singleton_defaults


@receiver(post_migrate)
def create_shop_defaults(sender, **kwargs):
    if sender.name != "shop":
        return
    ensure_singleton_defaults()
