# Generated by Django 4.1 on 2023-09-02 15:43

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cooker_app", "0002_alter_cookermodel_phone_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="cookermodel",
            name="email",
        ),
        migrations.RemoveField(
            model_name="cookermodel",
            name="password",
        ),
        migrations.AlterField(
            model_name="cookermodel",
            name="phone",
            field=models.CharField(
                max_length=17,
                unique=True,
                validators=[django.core.validators.MinLengthValidator(17)],
            ),
        ),
    ]
