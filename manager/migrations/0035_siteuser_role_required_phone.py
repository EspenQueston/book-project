from django.db import migrations, models


def backfill_phone(apps, schema_editor):
    SiteUser = apps.get_model('manager', 'SiteUser')
    SiteUser.objects.filter(phone='').update(phone='Non renseigné')


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0034_topuporder_userwallet_wallettransaction'),
    ]

    operations = [
        migrations.AddField(
            model_name='siteuser',
            name='role',
            field=models.CharField(choices=[('buyer', 'Acheteur'), ('seller', 'Acheteur & vendeur')], db_index=True, default='buyer', max_length=20, verbose_name='角色'),
        ),
        migrations.AddField(
            model_name='siteuser',
            name='seller_activated_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='卖家激活时间'),
        ),
        migrations.RunPython(backfill_phone, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='siteuser',
            name='phone',
            field=models.CharField(max_length=20, verbose_name='电话'),
        ),
    ]
