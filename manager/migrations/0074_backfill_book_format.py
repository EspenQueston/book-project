from django.db import migrations


def backfill_format(apps, schema_editor):
    """Set format from the same signal has_download()/inventory already used
    to infer digital-vs-physical, so every existing book's behavior is
    unchanged after this migration — format is just making that inference
    explicit, not changing it."""
    Book = apps.get_model('manager', 'Book')
    for book in Book.objects.all().iterator():
        has_download = bool(book.book_file) or bool(book.download_link)
        if has_download and book.inventory == 0:
            new_format = 'digital'
        elif has_download and book.inventory > 0:
            new_format = 'both'
        else:
            new_format = 'physical'
        if book.format != new_format:
            book.format = new_format
            book.save(update_fields=['format'])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('manager', '0073_book_format'),
    ]

    operations = [
        migrations.RunPython(backfill_format, noop_reverse),
    ]
