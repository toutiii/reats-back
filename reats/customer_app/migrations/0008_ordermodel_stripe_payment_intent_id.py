# Generated by Django 4.1 on 2024-10-05 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("customer_app", "0007_customermodel_stripe_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordermodel",
            name="stripe_payment_intent_id",
            field=models.CharField(max_length=100, null=True),
        ),
    ]
