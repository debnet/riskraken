# Generated by Django 3.2 on 2021-04-30 02:16

import django.core.validators
from django.db import migrations, models
import krakenapp.models


class Migration(migrations.Migration):

    dependencies = [
        ('krakenapp', '0006_rollback_player'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to=krakenapp.models.upload_to, validators=[django.core.validators.validate_image_file_extension, krakenapp.models.validate_image_size], verbose_name='image'),
        ),
    ]