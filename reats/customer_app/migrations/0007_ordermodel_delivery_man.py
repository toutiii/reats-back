# Generated by Django 4.1 on 2024-05-25 18:04

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("delivery_app", "0001_initial"),
        ("customer_app", "0006_addressmodel_is_enabled"),
    ]

    operations = [
        migrations.AddField(
            model_name="ordermodel",
            name="delivery_man",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="delivery_app.delivermodel",
            ),
        ),
    ]
