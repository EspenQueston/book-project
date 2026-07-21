from django.db import migrations


def backfill_primary_admin(apps, schema_editor):
    Manager = apps.get_model('manager', 'Manager')
    # The very first admin account (lowest id) becomes the Primary Admin —
    # in practice there is exactly one row at migration time (seeded by
    # build.sh), so this is unambiguous.
    first = Manager.objects.order_by('id').first()
    if first and not first.email:
        first.email = 'admin@duno360.com'
        first.role = 'admin'
        first.is_primary = True
        first.is_admin = True
        first.save(update_fields=['email', 'role', 'is_primary', 'is_admin'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0070_manager_email_manager_is_primary_manager_role_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_primary_admin, noop_reverse),
    ]
