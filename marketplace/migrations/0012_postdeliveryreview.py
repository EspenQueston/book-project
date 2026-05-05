# Generated manually

import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0032_vendor_notification'),
        ('marketplace', '0011_supermarketitem_vendor'),
    ]

    operations = [
        migrations.CreateModel(
            name='PostDeliveryReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('listing_kind', models.CharField(choices=[('book', 'Book'), ('product', 'Product'), ('course', 'Course'), ('supermarket', 'Supermarket')], db_index=True, max_length=20, verbose_name='商品类型')),
                ('listing_id', models.PositiveIntegerField(db_index=True, verbose_name='商品ID')),
                ('message', models.TextField(blank=True, default='', verbose_name='评价内容')),
                ('images', models.JSONField(blank=True, default=list, verbose_name='图片')),
                ('has_images', models.BooleanField(default=False, verbose_name='含图')),
                ('rating_product', models.PositiveSmallIntegerField(verbose_name='商品质量')),
                ('rating_service', models.PositiveSmallIntegerField(verbose_name='客服质量')),
                ('rating_delivery', models.PositiveSmallIntegerField(verbose_name='物流速度')),
                ('avg_rating', models.DecimalField(decimal_places=2, default=Decimal('0'), max_digits=3, verbose_name='均分')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('book_order_item', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='post_delivery_review', to='manager.orderitem', verbose_name='图书订单行')),
                ('marketplace_order_item', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='post_delivery_review', to='marketplace.marketplaceorderitem', verbose_name='市场订单行')),
                ('site_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_delivery_reviews', to='manager.siteuser', verbose_name='用户')),
            ],
            options={
                'verbose_name': '收货评价',
                'verbose_name_plural': '收货评价',
                'db_table': 'marketplace_post_delivery_review',
                'ordering': ['-avg_rating', '-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='postdeliveryreview',
            index=models.Index(fields=['listing_kind', 'listing_id', '-avg_rating'], name='marketplace__listing_6c8c87_idx'),
        ),
    ]
