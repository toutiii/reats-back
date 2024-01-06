from cooker_app.models import CookerModel, GenericUser
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=CookerModel)
def create_generic_user(
    sender,
    instance: CookerModel,
    created: bool = False,
    **kwargs,
):
    if created:
        GenericUser.objects.create(phone=instance.phone)
