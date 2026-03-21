import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

from manager.models import Book

# Check for Django book
print("=" * 60)
print("Checking Django Web开发指南 book in database...")
print("=" * 60)

books = Book.objects.filter(name__icontains='Django')
if books.exists():
    for book in books:
        print(f"\nBook ID: {book.id}")
        print(f"Book Name: {book.name}")
        print(f"Download Link: {book.download_link or 'None'}")
        print(f"Book File: {book.book_file or 'None'}")
        print(f"Has Download: {book.has_download()}")
        print(f"Download Type: {book.get_download_type()}")
        print(f"Download URL: {book.get_download_url()}")
else:
    print("\n❌ No books found with 'Django' in the name")

print("\n" + "=" * 60)
print("All books with download links or files:")
print("=" * 60)

books_with_downloads = Book.objects.exclude(download_link__isnull=True, download_link='').exclude(book_file__isnull=True, book_file='')
if books_with_downloads.exists():
    for book in books_with_downloads:
        print(f"\n📚 {book.name}")
        print(f"   Download Link: {book.download_link or 'None'}")
        print(f"   Book File: {book.book_file or 'None'}")
else:
    print("\n❌ No books with downloads found in database")
