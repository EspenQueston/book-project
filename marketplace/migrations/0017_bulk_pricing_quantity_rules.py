from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0016_min_order_quantity'),
    ]

    operations = [
        migrations.AddField(
            model_name='marketplacecartitem',
            name='pricing_rule_log',
            field=models.JSONField(blank=True, default=dict, verbose_name='价格规则日志'),
        ),
        migrations.AddField(
            model_name='marketplaceorderitem',
            name='pricing_rule_log',
            field=models.JSONField(blank=True, default=dict, verbose_name='价格规则日志'),
        ),
        migrations.AddField(
            model_name='product',
            name='max_order_quantity',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='最高购买数量'),
        ),
        migrations.AddField(
            model_name='product',
            name='pricing_rules',
            field=models.JSONField(blank=True, default=dict, verbose_name='动态价格规则'),
        ),
        migrations.AddField(
            model_name='product',
            name='quantity_step',
            field=models.PositiveIntegerField(default=1, verbose_name='购买数量步长'),
        ),
        migrations.AddField(
            model_name='supermarketitem',
            name='max_order_quantity',
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name='最高购买数量'),
        ),
        migrations.AddField(
            model_name='supermarketitem',
            name='pricing_rules',
            field=models.JSONField(blank=True, default=dict, verbose_name='动态价格规则'),
        ),
        migrations.AddField(
            model_name='supermarketitem',
            name='quantity_step',
            field=models.PositiveIntegerField(default=1, verbose_name='购买数量步长'),
        ),
    ]
