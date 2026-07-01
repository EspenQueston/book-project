# Generated manually to ensure deleting a vendor also deletes its shop listings.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0048_donationcampaign_and_more'),
        ('marketplace', '0018_marketplaceorder_city'),
    ]

    operations = [
        migrations.AlterField(
            model_name='course',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='courses', to='manager.vendor', verbose_name='卖家'),
        ),
        migrations.AlterField(
            model_name='product',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='products', to='manager.vendor', verbose_name='卖家'),
        ),
        migrations.AlterField(
            model_name='supermarketitem',
            name='vendor',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='supermarket_items', to='manager.vendor', verbose_name='卖家'),
        ),
    ]
