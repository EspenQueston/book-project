"""
Create E-commerce Tables for Cart and Order Functionality
Run this script to create missing tables in PostgreSQL
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'book_Project.settings')
django.setup()

def main():
    print("🛒 Creating E-commerce Database Tables...")
    
    try:
        # Create migrations for new models
        print("📝 Creating migrations...")
        execute_from_command_line(['manage.py', 'makemigrations', 'manager'])
        
        # Apply migrations
        print("🔄 Applying migrations...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        print("✅ E-commerce tables created successfully!")
        print("\n📊 Available tables now include:")
        print("- cart_item (for shopping cart)")
        print("- customer_order (for orders)")
        print("- order_item (for order details)")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()
