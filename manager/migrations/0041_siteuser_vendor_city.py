# Generated manually — city within department

from django.db import migrations, models

import manager.congo_locations


def backfill_city_from_department(apps, schema_editor):
    SiteUser = apps.get_model('manager', 'SiteUser')
    Vendor = apps.get_model('manager', 'Vendor')
    EmailVerification = apps.get_model('manager', 'EmailVerification')
    for Model in (SiteUser, Vendor, EmailVerification):
        for row in Model.objects.all():
            dept = getattr(row, 'location', '') or manager.congo_locations.DEFAULT_CONGO_LOCATION
            row.city = manager.congo_locations.default_city_for_department(dept)
            row.save(update_fields=['city'])


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0040_siteuser_vendor_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteuser',
            name='city',
            field=models.CharField(
                default=manager.congo_locations.DEFAULT_CONGO_CITY,
                max_length=64,
                verbose_name='Ville',
            ),
        ),
        migrations.AddField(
            model_name='vendor',
            name='city',
            field=models.CharField(
                default=manager.congo_locations.DEFAULT_CONGO_CITY,
                max_length=64,
                verbose_name='Ville',
            ),
        ),
        migrations.AddField(
            model_name='emailverification',
            name='city',
            field=models.CharField(
                blank=True,
                default=manager.congo_locations.DEFAULT_CONGO_CITY,
                max_length=64,
                verbose_name='Ville',
            ),
        ),
        migrations.RunPython(backfill_city_from_department, migrations.RunPython.noop),
    ]
