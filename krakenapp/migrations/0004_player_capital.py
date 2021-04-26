# Generated by Django 3.2 on 2021-04-25 23:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('krakenapp', '0003_claim_instead_of_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='player',
            name='capital',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to='krakenapp.territory', verbose_name='capitale'),
        ),
    ]
