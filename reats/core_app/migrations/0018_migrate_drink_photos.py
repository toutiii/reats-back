from django.db import migrations


def migrate_drink_photos(apps, schema_editor):
    DrinkModel = apps.get_model("core_app", "DrinkModel")
    DrinkImageModel = apps.get_model("core_app", "DrinkImageModel")

    for drink in DrinkModel.objects.all():
        if drink.photo:
            DrinkImageModel.objects.create(drink=drink, key=drink.photo, is_primary=True, position=0)


def rollback_drink_photos(apps, schema_editor):
    DrinkImageModel = apps.get_model("core_app", "DrinkImageModel")
    DrinkImageModel.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ("core_app", "0017_create_drinkimagemodel"),
    ]

    operations = [
        migrations.RunPython(migrate_drink_photos, rollback_drink_photos),
    ]
