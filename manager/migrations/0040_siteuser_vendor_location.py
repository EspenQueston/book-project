# Generated manually for Congo department location fields

from django.db import migrations, models

import manager.congo_locations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0039_rename_platform_es_vendor__a1b2c3_idx_platform_es_vendor__95faaa_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteuser',
            name='location',
            field=models.CharField(
                choices=manager.congo_locations.CONGO_DEPARTMENT_CHOICES,
                default=manager.congo_locations.DEFAULT_CONGO_LOCATION,
                max_length=64,
                verbose_name='Localisation',
            ),
        ),
        migrations.AddField(
            model_name='vendor',
            name='location',
            field=models.CharField(
                choices=manager.congo_locations.CONGO_DEPARTMENT_CHOICES,
                default=manager.congo_locations.DEFAULT_CONGO_LOCATION,
                max_length=64,
                verbose_name='Localisation',
            ),
        ),
        migrations.AddField(
            model_name='emailverification',
            name='location',
            field=models.CharField(
                blank=True,
                choices=manager.congo_locations.CONGO_DEPARTMENT_CHOICES,
                default=manager.congo_locations.DEFAULT_CONGO_LOCATION,
                max_length=64,
                verbose_name='Localisation',
            ),
        ),
    ]
