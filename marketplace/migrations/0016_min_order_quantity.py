from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('marketplace', '0015_add_course_stock'),
    ]

    operations = [
        migrations.AddField(
            model_name='product',
            name='min_order_quantity',
            field=models.PositiveIntegerField(default=1, verbose_name='最低购买数量'),
        ),
        migrations.AddField(
            model_name='supermarketitem',
            name='min_order_quantity',
            field=models.PositiveIntegerField(default=1, verbose_name='最低购买数量'),
        ),
    ]
