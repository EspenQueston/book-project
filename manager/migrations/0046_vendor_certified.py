from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0045_remove_vendor_vendor_is_official_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='is_certified',
            field=models.BooleanField(db_index=True, default=False, verbose_name='认证卖家'),
        ),
        migrations.AddField(
            model_name='vendor',
            name='certified_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='认证时间'),
        ),
    ]
