# Generated by Django 4.2.7 on 2025-06-02 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('land_management', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='landparcel',
            name='land_use',
        ),
        migrations.AddField(
            model_name='landparcel',
            name='active_title_expiry',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='landparcel',
            name='active_title_type',
            field=models.CharField(blank=True, choices=[('property_contract', 'Property Contract'), ('parcel_certificate', 'Parcel Certificate')], max_length=30, null=True),
        ),
        migrations.AddField(
            model_name='landparcel',
            name='property_type',
            field=models.CharField(choices=[('residential', 'Residential'), ('commercial', 'Commercial'), ('agricultural', 'Agricultural'), ('industrial', 'Industrial'), ('mixed', 'Mixed Use')], default='residential', max_length=20),
        ),
    ]
