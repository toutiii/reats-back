# Generated by Django 4.1 on 2023-10-01 17:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cooker_app", "0008_cookermodel_photo"),
    ]

    operations = [
        migrations.AlterField(
            model_name="dishmodel",
            name="category",
            field=models.CharField(
                choices=[
                    ("starter", "starter"),
                    ("dish", "dish"),
                    ("dessert", "dessert"),
                ],
                max_length=9,
            ),
        ),
    ]
