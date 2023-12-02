# Generated by Django 4.1 on 2023-10-29 13:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cooker_app", "0013_alter_cookermodel_photo"),
    ]

    operations = [
        migrations.CreateModel(
            name="DrinkModel",
            fields=[
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "unit",
                    models.CharField(
                        choices=[("liter", "liter"), ("centiliters", "centiliters")],
                        max_length=20,
                    ),
                ),
                ("country", models.CharField(max_length=50)),
                ("description", models.TextField(max_length=512, null=True)),
                ("name", models.CharField(max_length=128)),
                ("price", models.FloatField()),
                ("photo", models.CharField(max_length=512)),
                ("is_enabled", models.BooleanField(default=True)),
                ("capacity", models.IntegerField()),
                (
                    "cooker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="cooker_app.cookermodel",
                    ),
                ),
            ],
            options={
                "db_table": "drinks",
            },
        ),
    ]
