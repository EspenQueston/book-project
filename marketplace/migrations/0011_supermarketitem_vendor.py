# Generated manually for vendor-owned supermarket listings

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0031_order_shipping_address'),
        ('marketplace', '0010_flashsale'),
    ]

    operations = [
        migrations.AddField(
            model_name='supermarketitem',
            name='vendor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='supermarket_items',
                to='manager.vendor',
                verbose_name='卖家',
            ),
        ),
    ]
