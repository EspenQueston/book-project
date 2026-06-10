from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0043_vendor_is_official'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='city',
            field=models.CharField(blank=True, default='', max_length=100, verbose_name='城市'),
        ),
    ]
