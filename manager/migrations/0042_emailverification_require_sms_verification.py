# Generated manually — SMS fallback flag

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0041_siteuser_vendor_city'),
    ]

    operations = [
        migrations.AddField(
            model_name='emailverification',
            name='require_sms_verification',
            field=models.BooleanField(default=False, verbose_name='SMS OTP requis'),
        ),
    ]
