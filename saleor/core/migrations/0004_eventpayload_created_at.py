# Generated by Django 3.2.6 on 2021-12-13 08:31

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_auto_20211122_0927"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventpayload",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True, default=django.utils.timezone.now
            ),
            preserve_default=False,
        ),
    ]
