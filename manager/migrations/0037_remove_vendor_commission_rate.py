from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0036_platform_escrow_vendor_wallet'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vendor',
            name='commission_rate',
        ),
    ]
