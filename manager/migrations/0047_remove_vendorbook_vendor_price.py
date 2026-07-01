from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0046_vendor_certified'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vendorbook',
            name='vendor_price',
        ),
    ]
