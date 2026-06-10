from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0037_remove_vendor_commission_rate'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverification',
            name='phone_verified',
            field=models.BooleanField(default=False, verbose_name='Téléphone vérifié'),
        ),
    ]
