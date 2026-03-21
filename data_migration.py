"""
Data Migration Script: MySQL to PostgreSQL
Django Book Management System

This script exports data from MySQL and imports into PostgreSQL
without requiring special MySQL privileges.
"""

import os
import sys
import json
import django
from django.conf import settings
from django.core import serializers
from django.core.management import execute_from_command_line

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def setup_django_for_mysql():
    """Setup Django to connect to MySQL for data export"""
    
    # Temporarily modify settings for MySQL connection
    mysql_settings = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': 'db_book',
            'USER': 'bookuser',  # or 'root' if needed
            'PASSWORD': 'BookProject123!',  # Update with your MySQL password
            'HOST': '127.0.0.1',
            'PORT': '3306',
            'OPTIONS': {
                'charset': 'utf8mb4',
                'use_unicode': True,
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
    
    # Override database settings
    settings.DATABASES = mysql_settings
    
    # Setup Django with MySQL settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
    django.setup()

def setup_django_for_postgresql():
    """Setup Django to connect to PostgreSQL for data import"""
    
    # PostgreSQL settings (already in your settings.py)
    postgresql_settings = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'db_book',
            'USER': 'bookuser',
            'PASSWORD': 'BookProject123!',
            'HOST': '127.0.0.1',
            'PORT': '5432',
            'OPTIONS': {
                'client_encoding': 'UTF8',
            },
        }
    }
    
    # Override database settings
    settings.DATABASES = postgresql_settings
    
    # Setup Django with PostgreSQL settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
    django.setup()

def export_mysql_data():
    """Export data from MySQL using Django's serialization"""
    
    print("🔄 Exporting data from MySQL...")
    
    try:
        # Setup Django for MySQL
        setup_django_for_mysql()
        
        # Import models after Django setup
        from manager.models import Manager, Publisher, Book, Author
        
        # Export data using Django's serialization
        data_to_export = []
        
        # Export managers
        managers = Manager.objects.all()
        if managers:
            print(f"📋 Found {managers.count()} managers")
            for manager in managers:
                data_to_export.append({
                    'model': 'manager.manager',
                    'pk': manager.id,
                    'fields': {
                        'number': manager.number,
                        'password': manager.password,
                        'name': manager.name
                    }
                })
        
        # Export publishers
        publishers = Publisher.objects.all()
        if publishers:
            print(f"📋 Found {publishers.count()} publishers")
            for publisher in publishers:
                data_to_export.append({
                    'model': 'manager.publisher',
                    'pk': publisher.id,
                    'fields': {
                        'publisher_name': publisher.publisher_name,
                        'publisher_address': publisher.publisher_address
                    }
                })
        
        # Export books
        books = Book.objects.all()
        if books:
            print(f"📋 Found {books.count()} books")
            for book in books:
                data_to_export.append({
                    'model': 'manager.book',
                    'pk': book.id,
                    'fields': {
                        'name': book.name,
                        'description': getattr(book, 'description', ''),
                        'price': str(book.price),
                        'inventory': book.inventory,
                        'sale_num': book.sale_num,
                        'publisher': book.publisher.id
                    }
                })
        
        # Export authors
        authors = Author.objects.all()
        if authors:
            print(f"📋 Found {authors.count()} authors")
            for author in authors:
                # Get related books
                related_books = [book.id for book in author.book.all()]
                
                data_to_export.append({
                    'model': 'manager.author',
                    'pk': author.id,
                    'fields': {
                        'name': author.name,
                        'book': related_books
                    }
                })
        
        # Save exported data to JSON file
        export_file = 'mysql_data_export.json'
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(data_to_export, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Data exported successfully to {export_file}")
        print(f"📊 Exported {len(data_to_export)} records total")
        
        return True, export_file
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        print(f"🔧 Error details: {type(e).__name__}")
        return False, None

def import_postgresql_data(export_file):
    """Import data into PostgreSQL"""
    
    print("🔄 Importing data into PostgreSQL...")
    
    try:
        # Setup Django for PostgreSQL
        setup_django_for_postgresql()
        
        # Import models after Django setup
        from manager.models import Manager, Publisher, Book, Author
        
        # Load exported data
        with open(export_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Clear existing data (optional - be careful!)
        print("⚠️  Clearing existing PostgreSQL data...")
        Author.objects.all().delete()
        Book.objects.all().delete()
        Publisher.objects.all().delete()
        Manager.objects.all().delete()
        
        # Import in dependency order: Manager, Publisher, Book, Author
        
        # 1. Import Managers
        managers_data = [item for item in data if item['model'] == 'manager.manager']
        for item in managers_data:
            Manager.objects.create(
                id=item['pk'],
                number=item['fields']['number'],
                password=item['fields']['password'],
                name=item['fields']['name']
            )
        print(f"✅ Imported {len(managers_data)} managers")
        
        # 2. Import Publishers
        publishers_data = [item for item in data if item['model'] == 'manager.publisher']
        for item in publishers_data:
            Publisher.objects.create(
                id=item['pk'],
                publisher_name=item['fields']['publisher_name'],
                publisher_address=item['fields']['publisher_address']
            )
        print(f"✅ Imported {len(publishers_data)} publishers")
        
        # 3. Import Books
        books_data = [item for item in data if item['model'] == 'manager.book']
        for item in books_data:
            publisher = Publisher.objects.get(id=item['fields']['publisher'])
            Book.objects.create(
                id=item['pk'],
                name=item['fields']['name'],
                description=item['fields'].get('description', ''),
                price=item['fields']['price'],
                inventory=item['fields']['inventory'],
                sale_num=item['fields']['sale_num'],
                publisher=publisher
            )
        print(f"✅ Imported {len(books_data)} books")
        
        # 4. Import Authors
        authors_data = [item for item in data if item['model'] == 'manager.author']
        for item in authors_data:
            author = Author.objects.create(
                id=item['pk'],
                name=item['fields']['name']
            )
            # Add related books
            for book_id in item['fields']['book']:
                try:
                    book = Book.objects.get(id=book_id)
                    author.book.add(book)
                except Book.DoesNotExist:
                    print(f"⚠️  Book {book_id} not found for author {author.name}")
        print(f"✅ Imported {len(authors_data)} authors")
        
        print("🎉 Data import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        print(f"🔧 Error details: {type(e).__name__}")
        return False

def simple_mysql_export():
    """Alternative: Simple mysqldump with reduced privileges"""
    
    print("🔄 Attempting simple MySQL export without PROCESS privilege...")
    
    try:
        import subprocess
        
        # Try mysqldump with minimal privileges
        cmd = [
            'mysqldump',
            '-u', 'bookuser',  # Change to 'root' if needed
            '-p',
            '--single-transaction',
            '--no-tablespaces',
            '--skip-lock-tables',
            '--complete-insert',
            'db_book',
            'manager', 'publisher', 'book', 'author', 'author_book'
        ]
        
        print("Running command (you'll be prompted for password):")
        print(" ".join(cmd))
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            with open('mysql_simple_export.sql', 'w', encoding='utf-8') as f:
                f.write(result.stdout)
            print("✅ Simple MySQL export successful: mysql_simple_export.sql")
            return True
        else:
            print(f"❌ Simple export failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Simple export error: {e}")
        return False

def main():
    """Main migration function"""
    
    print("="*60)
    print("🔄 Django Book Management System")
    print("   MySQL to PostgreSQL Data Migration")
    print("="*60)
    
    print("\n📋 Available Migration Methods:")
    print("1. Django-based export (recommended)")
    print("2. Simple mysqldump (alternative)")
    print("3. Skip export and create sample data")
    
    choice = input("\nSelect method (1/2/3): ").strip()
    
    export_success = False
    export_file = None
    
    if choice == "1":
        print("\n🔄 Using Django-based export...")
        export_success, export_file = export_mysql_data()
        
    elif choice == "2":
        print("\n🔄 Using simple mysqldump...")
        export_success = simple_mysql_export()
        export_file = 'mysql_simple_export.sql'
        
    elif choice == "3":
        print("\n⏭️  Skipping export, will create sample data...")
        export_success = True
        export_file = None
        
    else:
        print("❌ Invalid choice. Exiting.")
        return
    
    if export_success and export_file and choice == "1":
        print(f"\n🔄 Proceeding with PostgreSQL import...")
        import_success = import_postgresql_data(export_file)
        
        if import_success:
            print("\n🎉 Migration completed successfully!")
        else:
            print("\n❌ Migration failed during import.")
            
    elif choice == "3":
        print("\n🔄 Creating sample data for PostgreSQL...")
        # Import the existing migration script
        try:
            from migrate_to_postgresql import create_sample_data, test_database_connection
            
            setup_django_for_postgresql()
            
            if test_database_connection():
                create_sample_data()
                print("\n🎉 Sample data creation completed!")
            else:
                print("\n❌ Database connection failed.")
                
        except ImportError:
            print("❌ Could not import migration functions.")
            
    else:
        print("\n📋 Next Steps:")
        print("1. Fix MySQL permissions and try again")
        print("2. Or manually create sample data")
        print("3. Or use PostgreSQL with fresh data")

if __name__ == "__main__":
    main()
