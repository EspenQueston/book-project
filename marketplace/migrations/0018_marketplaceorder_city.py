from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0017_bulk_pricing_quantity_rules'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketplaceorder',
            name='city',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='城市'),
        ),
    ]
