# Duno360 Official Store — add is_official flag on Vendor

from django.db import migrations, models


def bootstrap_official_store(apps, schema_editor):
    from manager.official_store import ensure_official_store
    ensure_official_store(backfill=True)


class Migration(migrations.Migration):
    # RunPython updates rows; PostgreSQL cannot CREATE INDEX in the same txn.
    atomic = False

    dependencies = [
        ('manager', '0042_emailverification_require_sms_verification'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='is_official',
            field=models.BooleanField(default=False, verbose_name='官方直营店'),
        ),
        migrations.RunPython(bootstrap_official_store, migrations.RunPython.noop),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['is_official'], name='vendor_is_official_idx'),
        ),
    ]
