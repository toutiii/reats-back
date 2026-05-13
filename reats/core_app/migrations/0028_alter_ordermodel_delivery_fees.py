from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core_app", "0027_merge_20260429_0437"),
    ]

    operations = [
        migrations.AlterField(
            model_name="ordermodel",
            name="delivery_fees",
            field=models.FloatField(),
        ),
    ]
