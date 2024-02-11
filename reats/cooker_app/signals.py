from typing import Union

from cooker_app.models import CookerModel, GenericUser
from customer_app.models import CustomerModel
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=CookerModel)
@receiver(post_save, sender=CustomerModel)
def create_generic_user(
    sender,
    instance: Union[CookerModel, CustomerModel],
    created: bool = False,
    **kwargs,
):
    try:
        GenericUser.objects.get(phone=instance.phone)
    except GenericUser.DoesNotExist:
        if created:
            GenericUser.objects.create(phone=instance.phone)
